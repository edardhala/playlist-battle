# Architecture Decision Records

## 1. Backend language and framework: Python + Flask
Date: 2026-10-05
Status: Decided
Context:  This is a small web app with server rendered pages and a few JSON endpoints. I chose Python with Flask, Jinja templates, and SQLite using the built in sqlite3 module. I decided not to use an ORM.
I also considered Django, but it comes with features like an admin panel, ORM and authentication that would be unnecessary for a small project like this. I also considered FastAPI, but features like async support and automatic API documentation aren't very useful for this app. This keeps the project simple with few dependencies and code that I can easily understand from start to finish. The downside is that I have to write the SQL myself and decide how to structure the project, since Flask doesn't enforce a specific structure.
