# Technical Decisions

## Stack justification
- Django + DRF: mature ecosystem for rapid development, auth, and admin.
- PostgreSQL: strong relational integrity, indexing, and JSON support.
- SimpleJWT: proven JWT implementation with refresh rotation and blacklist.
- pytest: fast feedback and strong fixture ecosystem.
- ruff + mypy: keep code quality high and catch common defects.

## Architecture overview
- Layering:
  - Models: represent core entities.
  - Services: transactional business logic, validation, race-condition protection.
  - API views/serializers: request/response validation and permission gates.
  - Middleware: tenant context and audit logging.

## Key design decisions
- Tenant isolation via explicit query scoping and middleware.
- Deterministic rollout using hashing to avoid per-request randomness.
- Approval workflow enforced in service layer to prevent bypass.

## Tradeoffs
- Centralized service layer increases indirection but makes invariants enforceable.
- Mypy strictness is set to a realistic baseline; can be tightened over time.
