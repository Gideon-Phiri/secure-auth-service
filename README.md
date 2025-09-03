# Secure Auth Service

<div align="left">

| CI | Coverage | Security Scan |
|----|----------|---------------|
| _Add GitHub Action badge here_ | _Add coverage badge_ | _Add SAST badge_ |

</div>

FastAPI-based authentication & user management service with production-minded security controls (JWT auth, email verification, rate limiting, structured security logging) and a fully isolated, reliable test suite.

## Features

- JWT access & refresh tokens
- Password complexity & account lockout
- Email verification workflow
- (Toggleable) rate limiting via SlowAPI
- Structured security & request logging (JSON)
- Security headers middleware & request IDs
- Admin user management endpoints
- Database migrations (Alembic / SQLModel)
- 100% passing automated tests (pytest + httpx + asyncio)

## Architecture Overview

Component | Tech
----------|-----
API Framework | FastAPI
DB Layer | SQLModel (async) + PostgreSQL (prod) / SQLite in tests
Migrations | Alembic
Rate Limiting | SlowAPI (conditional in tests)
Auth | JWT (HS256) access + refresh, password hashing (PassLib / bcrypt)
Logging | Python logging w/ structured security events
Container | Docker / docker-compose
Tests | pytest, pytest-asyncio, httpx AsyncClient

## Quickstart (Local Development)

1. Copy environment file:
	```bash
	cp .env.example .env
	```
2. Generate strong secrets:
	```bash
	python -c "import secrets;print('SECRET_KEY='+secrets.token_urlsafe(32))"
	python -c "import secrets;print('DB_PASSWORD='+secrets.token_urlsafe(24))"
	```
3. Update `.env` with generated values (never commit secrets).
4. Build & start services:
	```bash
	docker compose up --build -d
	```
5. Run database migrations:
	```bash
	docker compose exec web alembic upgrade head
	```
6. Open interactive docs: http://localhost:8000/docs

### Minimal Ops Cheat Sheet

Action | Command
-------|--------
Launch stack | `docker compose up -d`
Apply migrations | `docker compose exec web alembic upgrade head`
Create migration | `docker compose exec web alembic revision --autogenerate -m "msg"`
Run tests | `pytest -q`
Tail logs | `docker compose logs -f web`
Open docs | http://localhost:8000/docs

Detailed operations runbook: see `OPS.md`.

## Environment Variables

Key | Purpose | Notes
----|---------|------
`SECRET_KEY` | JWT signing key | Long, random, keep secret
`DATABASE_URL` | SQLAlchemy URL | PostgreSQL in production
`ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | Default 15
`REFRESH_TOKEN_EXPIRE_MINUTES` | Refresh token TTL | Longer lived
`SMTP_HOST/PORT/USER/PASSWORD` | Email sending | For verification mails
`EMAIL_FROM` | From address | Defaults to SMTP user

## Database & Migrations

- Models defined in `app/db/models.py` (SQLModel).
- Run migrations with Alembic:
  ```bash
  docker compose exec web alembic revision --autogenerate -m "change"
  docker compose exec web alembic upgrade head
  ```

## Testing

Run full suite:
```bash
pytest -q
```

Highlights:
- In-memory SQLite per test function (fast & isolated)
- Rate limiter disabled by default via `conditional_limit` decorator
- Explicit rate limit tests enable real limits using `enable_test_rate_limits()`
- Structured logging tested with mocks

### Rate Limiting Strategy

Routes use `@conditional_limit("X/minute")` wrappers instead of binding directly to SlowAPI at import. In production this behaves like `@limiter.limit(...)`. In tests:
- Default: no-op to avoid flaky global counters
- Explicit tests call `enable_test_rate_limits()` (which resets limiter state) then exercise actual limits

Helpers in `app/core/rate_limit.py`:
- `conditional_limit` – decorator
- `enable_test_rate_limits()` / `disable_test_rate_limits()` – flip behavior
- `reset_rate_limit_wrappers()` – clears cached wrapped callables (used in tests)

## Security Features

Area | Details
-----|--------
Password Policy | Length, upper, lower, digit, special char
Account Lockout | After repeated failed logins (with unlock timer)
Email Verification | Token-based confirmation before login allowed
Security Logging | `SecurityEvent` JSON lines (success/failure, IP, UA)
Headers | (Configured in middleware) request ID, security headers
Rate Limiting | Per-endpoint with opt-in enablement for tests

## Admin Endpoints (Protected)

Endpoint | Purpose
---------|--------
`GET /users/` | List users
`POST /users/` | Create user (optional superuser)
`GET /users/{id}` | Fetch user by ID
`PUT /users/{id}` | Update user
`POST /users/{id}/activate` | Activate user
`POST /users/{id}/deactivate` | Deactivate user
`DELETE /users/{id}` | Delete user

Requires Authorization header with a valid admin JWT.

## Logging

Security events & request logs are structured for consumption by log aggregation (ELK / Loki). Each event includes timestamps (ISO 8601), user ids where available, IP, user agent, and an event type.

## Development Workflow

Common tasks:
Task | Command
-----|--------
Run tests | `pytest -q`
Lint (add later) | `ruff check .` (example)
Generate migration | `alembic revision --autogenerate -m "msg"`
Apply migration | `alembic upgrade head`

## Production Notes

- Use a managed Postgres with SSL & proper IAM
- Store secrets in a secrets manager (AWS Secrets Manager, Vault, etc.)
- Rotate JWT signing key with versioning strategy
- Add HTTPS (reverse proxy or CDN) – don't rely on dev settings
- Forward logs to centralized system & add alerting on anomalies
- Consider adding refresh token rotation & revoke lists

## Extending

Add a new endpoint:
1. Create a router file under `app/api/v1/`
2. Import & include it in `app/main.py`
3. Add schemas (Pydantic / SQLModel) as needed
4. Add tests (aim for fast, independent design like existing suite)

## License

MIT

---
For security hardening steps see `SECURITY_CHECKLIST.md`.
