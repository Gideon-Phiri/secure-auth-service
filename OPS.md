# Operations Runbook (Secure Auth Service)

Purpose: Fast reference for deploying, monitoring, troubleshooting, and maintaining the service.

## 1. Environments

Env | DB | Notes
----|----|------
local | Docker Postgres | DEBUG logs enabled
staging | Managed Postgres | Email sandbox creds
production | Managed Postgres (HA) | Strict security headers, real SMTP

## 2. Required Environment Variables

Minimal (must exist):
- SECRET_KEY
- DATABASE_URL
- ACCESS_TOKEN_EXPIRE_MINUTES
- REFRESH_TOKEN_EXPIRE_MINUTES
- SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD (if email verification active)
- EMAIL_FROM

## 3. Deployment (Container Image)

Build:
```bash
docker build -t secure-auth:$(git rev-parse --short HEAD) .
```
Push (example registry):
```bash
docker tag secure-auth:$(git rev-parse --short HEAD) ghcr.io/your-org/secure-auth:$(git rev-parse --short HEAD)
docker push ghcr.io/your-org/secure-auth:$(git rev-parse --short HEAD)
```
Run migration (one-shot job / init container):
```bash
alembic upgrade head
```

## 4. Health & Readiness

Endpoint | Purpose
---------|--------
`GET /health` | Liveness check (app + DB session attempt)

Automate probes (Kubernetes example):
- livenessProbe: `/health`
- readinessProbe: `/health`

## 5. Logging & Security Events

Log Types:
- Request logs: request/response with request ID
- Security events: JSON lines with event_type (auth_success, auth_failure, user_registration, account_lockout, etc.)

Recommendation: Ship stdout to centralized logging (e.g. Loki / ELK). Filter by `SECURITY_EVENT` / `SECURITY_ALERT` substrings.

## 6. Rate Limiting Behavior

- Production: SlowAPI enforced via `conditional_limit` decorator.
- Tests: Disabled by default; explicit tests invoke `enable_test_rate_limits()`.
- To globally throttle more aggressively, adjust decorator strings in route modules.

## 7. Common Operational Tasks

Task | Action
-----|-------
Reset locked account | Manually clear `locked_until` & `failed_attempts` in users table
Promote user to admin | Set `is_superuser = true`
Force password reset | Replace `hashed_password` with new hash (invalidate sessions by rotating SECRET_KEY if needed)
Revoke tokens globally | Rotate `SECRET_KEY` (invalidates all existing JWTs)

## 8. Backup & Restore (Database)

Example (Postgres):
```bash
pg_dump "$DATABASE_URL" > backup.sql
psql "$DATABASE_URL" < backup.sql
```
Automate daily dumps + secure storage (encrypted bucket / snapshot).

## 9. Incident Response Quick Checks

Scenario | Checklist
---------|----------
Spike in 401 | Check brute force / enable WAF rules
Excess 429 | Increase limits, investigate abusive IPs
Account lockouts | Validate correctness; possible credential stuffing
DB latency | Inspect slow queries; check connection pool saturation
High memory | Profile with sampling (py-spy) in staging clone

## 10. Metrics Suggestions (Add Prometheus Exporter Later)

Metric | Rationale
-------|----------
login_success_total | Auth throughput
login_failure_total | Credential attack detection
rate_limit_exceeded_total | Abuse detection
active_users_total | Growth insight
request_latency_seconds | SLA tracking

## 11. Security Hardening Next Steps

See `SECURITY_CHECKLIST.md` plus:
- Implement refresh token rotation & blacklist on compromise
- Add CSP & stricter security headers (helmet-equivalent policy)
- Add Prometheus / OpenTelemetry instrumentation
- Consider multi-region deployment + DB replicas

## 12. Disaster Recovery

Category | Target
---------|-------
RPO | <= 15 min (backup frequency)
RTO | < 1 hour (container redeploy + migration run)

## 13. Secrets Management

Use external secrets store in production (AWS SM, Vault, Doppler, etc.):
- Inject at runtime via environment or sidecar agent
- Never bake secrets into image layers

## 14. Performance Tuning Hints

- Ensure `uvicorn --workers N` behind a process manager (e.g., gunicorn) if high concurrency
- Enable DB connection pooling sized to 2–4x worker count (async engine handles pooling)
- Consider moving expensive email sends to async task queue (e.g., Celery / RQ) for high volume

## 15. Testing & Release Flow

1. Branch & PR -> run CI (lint + tests)
2. Auto build image on main merge
3. Staging deploy & smoke test
4. Tag release (semantic version)
5. Promote image to production

## 16. Troubleshooting Cheats

Symptom | Command/Action
-------|----------------
Hanging request | Check logs for missing await / DB lock
Frequent 429 | Inspect limiter key collisions (IP/proxy headers)
Login always 401 | Confirm email verification + password hash logic
Migration failed | Re-run with `--sql` to inspect generated SQL

## 17. Support Scripts

Scripts in `scripts/` (placeholders for now) can be extended for automated backup/restore or migrations.

---
Keep this file short, actionable, and revisited after each major feature.
