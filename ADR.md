# Architecture Decision Records

## 1. Backend language and framework: Python + Flask
Date: 2026-10-05
Status: Decided
Context: This is a small web app with server rendered pages and a few JSON endpoints. 
Decision: I chose Python with Flask, Jinja templates, and SQLite using the built in sqlite3 module. I decided not to use an ORM.
Alternatives considered: I also considered Django, but it comes with features like an admin panel, ORM and authentication that would be unnecessary for a small project like this. I also considered FastAPI, but features like async support and automatic API documentation aren't very useful for this app.
Consequences: This keeps the project simple with few dependencies and code that I can easily understand from start to finish. The downside is that I have to write the SQL myself and decide how to structure the project, since Flask doesn't enforce a specific structure.

## 2. Splitting the app into two independent domains
Date: 2026-10-06
Status: Decided
Context: The app has to be easy to split into separate services later, so the two feature areas should not depend on each other's code or tables.
Decision: Rooms and Battle each get their own folder with a `service.py` for the rules and a `routes.py` for the web pages. Battle will only store a room's id and never read the rooms tables directly. 
Alternatives considered: One big `app.py` with all routes and SQL in it. It is quicker to start, but the two domains would get mixed together and would be hard to separate later.
Consequences: Each domain can be tested on its own and could become its own service later. The cost is a few more files and passing ids between domains instead of joining tables.

## 3. How the two domains' data is connected in SQLite
Date: 2026-10-09
Status: Decided
Context: Rooms owns the `rooms` and `members` tables and Battle owns the `songs` and `votes` tables, but every song has to belong to a room.
Decision: `songs.room_id` stores the room's id as a plain number, with no foreign key to `rooms` and no JOINs across the two domains. Inside Battle, `votes.song_id` points to `songs`, and `UNIQUE (song_id, voter)` stops a person from voting twice for the same song.
Alternatives considered: A foreign key from `songs.room_id` to `rooms.id` with JOINs between the tables. The database would check that the room exists, but the two domains would be tied together and could not be moved into separate databases later.
Consequences: Battle could move to its own service and database later without changes. The cost is that the database can't stop a song from pointing to a room that doesn't exist, so the battle pages check that the room exists before adding a song.

## 4. Testing approach
Date: 2026-10-11
Status: Decided
Context: The assignment needs at least 70% coverage on the core business logic and I want tests that catch broken rules, not tests that only check Flask works.
Decision: Most tests call the functions in `rooms/service.py` and `battle/service.py` directly, using an in-memory SQLite database so every test starts empty and runs fast. They cover the rules: name checks, room codes, joining, one vote per person, duplicate songs, the hot score and playing the winner. A smaller set of page tests uses Flask's test client to check the main paths and error messages. The hot score tests use a fixed time so they always give the same result. Result: 47 tests and 98% coverage, measured with `pytest --cov`.
Alternatives considered: Browser tests with a tool like Selenium that click through the real pages. They test what a user sees, but they are slow, need a browser installed, and break when the design changes, so they are not worth it for an app this size.
Consequences: The rules are fully tested and can be changed with confidence. The HTML and CSS are tested less: the tests check that the right text and buttons appear, but not how the pages look, so design problems have to be checked by hand in the browser.

## 5. Not building user accounts or login
Date: 2026-10-12
Status: Decided
Context: The app needs to know who adds a song, who votes and who the host is, but people use it with friends for one evening and won't want to sign up first.
Decision: There are no accounts, passwords or sessions. After you create or join a room, your name is kept in the address (`?me=Ana`) and sent in a hidden `me` field when you add a song, vote or play the winner.
Alternatives considered: Login with a password, or Flask sessions with a signed cookie. Both would stop people from pretending to be someone else, but they need a secret key, password hashing and more pages, which is too much for this project and slows down joining a room.
Consequences: Joining a room takes a few seconds. The cost is that anyone can change the name in the address or the hidden field and vote, remove votes or play songs as someone else, including the host. If the app had real users, sessions would be the first thing to add.

## 6. The split: rooms and battle as two services
Date: 2026-11-18
Status: Decided
Context: Assignment 2 asks for one service per feature domain, along the seam from ADR-2. Rooms owned `rooms` and `members`, Battle owned `songs`, `votes` and `played`, and Battle only kept a room's id (ADR-3).
Decision: The seam stayed where ADR-2 put it. Only one call crosses it: Battle calls `GET /rooms/{code}` on Rooms (found through `ROOMS_URL`, 2 second timeout) to get the room id and members, and checks that the person is a member, or the host for playing, before adding a song, voting or playing. The UI calls both services for everything else. If Rooms is down, writes return 503 with "Rooms are not available right now", and the playlist still loads for rooms Battle has seen before, using the room id it remembered, with `rooms_available: false`.
Alternatives considered: Letting the UI check membership, which anyone could skip by calling Battle directly. Copying members into Battle's database, which would drift out of sync.
Consequences: ADR-2 held: the split needed one endpoint and no shared tables. Every write in Battle now makes one HTTP call, so writes are slower and fail when Rooms is down, but reading the playlist still works.

## 7. Data and migrations
Date: 2026-11-18
Status: Decided
Context: The monolith used one SQLite file. Now each service has its own SQL Server database and a login that cannot open the other one, and the schema has to change in place once the databases hold data.
Decision: Each service has numbered SQL files in `migrations/` and a small runner in `db.py` that runs at startup. It takes a lock with `sp_getapplock`, runs every file not yet listed in `schema_migrations` in name order, and records each file in the same transaction as its changes. No data was copied from SQLite, since rooms only last one evening. `songs.room_id` is a plain number with no foreign key (ADR-3), and Battle checks the room through Rooms before writing. Recovery plan: applied files are never edited and there are no down migrations. A failing migration rolls back, the new revision never becomes ready and the old one keeps serving. A wrong migration is fixed with a new one, and if it damaged data, the database is restored to a point before the deploy from Azure SQL's automatic backups.
Alternatives considered: Alembic, which needs SQLAlchemy while the services use plain SQL with pymssql. Creating tables on first boot as in Assignment 1, which cannot change a table that holds rows.
Consequences: Migrations are plain SQL I can read and test, and a second boot applies nothing. Integrity across the seam is lost: if a room were deleted, its songs would stay in Battle. Rooms are never deleted, so this is accepted.

## 8. Serverless hosting on Azure
Date: 2026-11-20
Status: Decided
Context: The system runs on my Azure for Students subscription and should cost nothing while nobody uses it. Container Apps scale to zero and the serverless databases pause after 60 minutes idle, so the first visitor after a quiet period meets a cold container and maybe a paused database.
Decision: Everything is in `rg-ehala-ieu2024` (`italynorth`): the managed identity `ehala-ieu2024-github`, the Consumption environment `ehala-ieu2024-env` with `ehala-ieu2024-rooms` and `ehala-ieu2024-battle` (0.25 vCPU, 0 to 1 replicas), the server `ehala-ieu2024-sql` with one serverless database per service on the free offer, the storage account `ehalaieu2024ui` for the UI, and the Log Analytics workspace `ehala-ieu2024-logs` for the containers' logs. Images are public on GHCR. Container Apps bill only while a replica runs and the monthly free grant covers this app; the free offer gives each database 100,000 vCore seconds a month and pauses it instead of charging; storage costs cents; the workspace is pay per use, free up to 5 GB a month and keeps logs for 30 days. The deploy job creates the workspace if it is missing and connects the environment to it, so it is not made by hand. On a cold start, `db.connect` retries for about a minute (1 to 30 second waits) while the database resumes, then runs the migrations. If the database is down during a request, the service answers with a JSON 503. The UI gives up after 45 seconds and shows "it is starting up, try again", and the room page reloads every 5 seconds. With at most one replica, migrations never run twice at once, and the `sp_getapplock` lock from ADR-7 covers it anyway. The post-deploy health check waits up to about 10 minutes.
Alternatives considered: `min-replicas 1`, or a database without auto-pause, which remove the wait but cost money every hour. No log workspace, reading only the live log stream with `az containerapp logs show`, which I started with but which loses the logs of a stopped replica.
Consequences: Idle cost is close to zero, and the price is a first visit of up to a minute after a quiet hour. Logs from earlier replicas, such as the migration lines, can still be queried later. At 100x traffic I would keep one replica always on and allow more, run migrations as a pipeline step instead of at startup, use a connection pool, move to a paid database without auto-pause, replace Battle's in-memory room cache with a short cache of members shared by all replicas, and add alerts on the logs and the health check.

## 9. Pipeline and testing
Date: 2026-11-21
Status: Decided
Context: Every push should be checked, and nothing should reach Azure unless the same commit passed. Battle depends on Rooms over HTTP, so the seam needs its own tests, but running both services and a database in every test is slow.
Decision: The `CI` workflow runs on every push and pull request. The `test` job runs once per service, with a SQL Server container: `ruff check`, then `pytest` with coverage, failing under 70%. Tests use a real SQL Server, not SQLite, so the migrations and queries run exactly as on Azure, and each run creates its own database. The `validate` job checks `system.yaml` against `system.schema.json` and both OpenAPI files. The `images` job needs both, and pushes images tagged with the commit SHA only on `main`. The `deploy` job needs `images`, so it only runs when CI passed on the same commit, and it fails if `/health` does not answer. The cross-seam tests in `services/battle/tests/test_cross_seam.py` replace Rooms with a stub: a small Flask app on a real port that returns rooms in the same shape as `GET /rooms/{code}`, and can be made slow or return 500. They check the real HTTP client, the timeout, the 403 for non-members, the 503 when Rooms is down and the cached room id for reads. `tests/e2e/test_compose_stack.py` runs the same story against the whole compose stack, including stopping Rooms, and I run it by hand before merging.
Alternatives considered: Running the compose stack in CI for every push, which is slower and depends on Docker in the runner. Contract testing tools such as Pact, which are a lot of setup for one endpoint.
Consequences: A push gets an answer in a few minutes, and a broken test or schema blocks the deploy. The stub can drift from the real Rooms, so the stub returns the shape in `services/rooms/openapi.yaml`, and the end-to-end test covers the real pair. Deliberately not tested: the UI JavaScript, which is small and checked by hand; Azure itself (cold starts, the database resuming, OIDC), which is checked by the post-deploy health check and the logs; and load.
