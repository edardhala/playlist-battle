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
