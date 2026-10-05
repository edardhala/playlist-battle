# Architecture Decision Records

## 1. Backend language and framework: Python + Flask
Date: 2026-10-05
Status: Decided
Context: The app is a small single-process web app with server-rendered pages and a few JSON endpoints, and I have to be able to explain all of the code myself.
Decision: Use Python with Flask, Jinja templates, and the built-in `sqlite3` module (no ORM).
Alternatives considered: Django, rejected because its admin, ORM and auth are far more than two small domains need. FastAPI, rejected because its main benefits (async, automatic API docs) don't matter for server-rendered pages polled by a few dozen users per room.
Consequences: Very few dependencies and code I can read end to end; in exchange I write my own SQL and structure the project myself, since Flask doesn't enforce one.
