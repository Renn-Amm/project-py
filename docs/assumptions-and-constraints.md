# Assumptions and Constraints

## Assumptions
- Tenants are attached to users (single-tenant per user) in the current model.
- Environments are limited to development/staging/production.

## Simplifications
- Dashboard is server-rendered using Django templates (no SPA).
- Local dev uses docker-compose with Postgres.

## Known limitations
- Full-featured tenant membership (many-to-many users<->tenants) is not implemented.
- Fine-grained per-flag permissions are not implemented.

## Postponed features
- Rate-limited admin actions.
- Advanced experiment statistics.
