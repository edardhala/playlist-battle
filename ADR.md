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
