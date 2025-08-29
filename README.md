# Secure Auth Service

Production-style authentication service built with FastAPI, PostgreSQL, Docker, and GitHub Actions.

Quickstart:

1. Copy `.env.example` to `.env` and adjust values.
2. docker compose up --build
3. docker compose exec web alembic upgrade head
4. Open http://localhost:8000/docs
