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
Context: Assignment 2 asks for one service per feature domain, along the seam from ADR-2. In the monolith, Rooms owned `rooms` and `members`, Battle owned `songs`, `votes` and `played`, and Battle only kept a room's id (ADR-3).
Decision: The seam stayed where ADR-2 put it. `services/rooms` owns rooms and members, `services/battle` owns songs, votes and played songs. Only one thing crosses the seam: Battle calls `GET /rooms/{code}` on Rooms, which returns the room's id and its members. Battle uses this server side before adding a song, voting or playing, to check that the person is a member and, for playing, the host. Battle finds Rooms through `ROOMS_URL` and waits at most `ROOMS_TIMEOUT_S` (2 seconds). The UI calls both services directly for everything else. If Rooms is down, adding, voting and playing return 503 with "Rooms are not available right now", and the playlist still loads for rooms Battle has already seen, using the room id it remembered, with `rooms_available: false`.
Alternatives considered: Letting the UI check membership and then call Battle. It needs no call between services, but anyone could skip the check by calling Battle directly, and the assignment needs one server side flow. Copying members into Battle's database. Battle could then work with Rooms down, but the two copies would drift apart and it would need events or a job to keep them in sync.
Consequences: ADR-2 held, since the split only needed one endpoint and no shared tables. The cost is one HTTP call on every write in Battle, which makes writes slower and makes them fail when Rooms is down. Reading the playlist still works in that case, which is the part people look at most.

## 7. Data and migrations
Date: 2026-11-18
Status: Decided
Context: The monolith used one SQLite file. Now each service has its own SQL Server database (locally two databases in one container, on Azure two serverless databases on one server) and its own login that cannot open the other database. The schema has to change in place once the databases hold data.
Decision: Each service has numbered SQL files in `migrations/` and a small runner in `db.py` that runs at startup. It takes a lock with `sp_getapplock`, creates `schema_migrations` if needed, runs every file not listed there in name order, and records each file in the same transaction as its changes, so a migration is either fully applied and recorded or not applied at all. No data was copied from the old SQLite file: rooms only last one evening, so the new databases start empty. The foreign key from `members` to `rooms` stays inside Rooms. `songs.room_id` is a plain number with no foreign key, as in ADR-3, and Battle checks the room through Rooms before writing. Recovery plan for a bad migration in production: applied files are never edited and there are no down migrations. A migration that fails rolls back, the new revision never becomes ready, and Container Apps keeps the old revision serving. A migration that succeeds but is wrong is fixed with a new migration. If it damaged data, the database is restored to a point in time before the deploy from Azure SQL's automatic backups, and the restored copy replaces the broken one.
Alternatives considered: Alembic, which tracks versions and can generate migrations, but it needs SQLAlchemy, and the services use plain SQL with pymssql. Creating the tables on first boot as in Assignment 1, which cannot change a table that already holds rows.
Consequences: Migrations are plain SQL that I can read and test, and a second boot applies nothing. The lock means two replicas starting at once cannot run the same migration twice, even though Azure runs at most one. Integrity across the seam is lost: if a room were deleted, its songs would stay in Battle. Rooms are never deleted today, so this is accepted. Writing migrations by hand means mistakes in SQL Server syntax are only caught by the tests that run them against a real SQL Server.
