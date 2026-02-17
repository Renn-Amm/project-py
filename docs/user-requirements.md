# User Requirements

## Target users

## Tenant Owner
- Manage tenant, environments, users, and policies.
- Approve high-risk production changes.

## Product Manager
- Define flags, rollouts, targeting rules, and experiments.
- Request approvals for production changes.

## Developer
- Integrate evaluation API in services/clients.
- Debug flag behavior via audit logs and analytics.

## Analyst
- Inspect adoption, evaluation counts, and experiment outcomes.

## Functional requirements
- Multi-tenant isolation for all data access.
- Multi-environment support per tenant.
- Feature flags with variants and deterministic percentage rollout.
- Targeting rules against user attributes.
- Experiment mode with control/treatment support.
- Flag dependencies.
- Time-based activation and expiration.
- Stale flag detection.
- Risk levels and approval workflow for high-risk production changes.
- Full audit logging for all mutations.
- Analytics tracking of evaluations.
- Secure evaluation API endpoint with throttling.

## Non-functional requirements
- Security: strict tenant isolation, RBAC, object-level permissions.
- Reliability: transactional updates, race-condition protection on sensitive writes.
- Performance: evaluation endpoint targeting < 100ms, proper indexing, caching option.
- Operability: production settings, Docker/Gunicorn, health checks.

## How the implementation satisfies the requirements
- Tenant isolation: enforced by tenant scoping on queries and middleware context.
- RBAC: role hierarchy with explicit checks on mutation endpoints.
- Approval workflow: service-layer enforcement for production high-risk changes.
- Deterministic rollout: SHA-256 hashing based assignment.
- Audit + analytics: write-side middleware/services track mutations and evaluations.
