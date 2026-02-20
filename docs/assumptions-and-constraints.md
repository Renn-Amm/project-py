# Assumptions and Constraints

## Assumptions
- Organizations are attached to users (single-organization per user) in the current model.
- Projects are the primary authorization boundary under an organization.

## Simplifications
- Dashboard is server-rendered using Django templates (no SPA).
- Local dev uses docker-compose with Postgres.

## Known limitations
- Full-featured org memberships (many-to-many users<->organizations) is not implemented.
- Fine-grained per-task permissions beyond role + membership are not implemented.

## Postponed features
- Rate-limited admin actions.
- More advanced analytics (trend charts, per-project throughput).
