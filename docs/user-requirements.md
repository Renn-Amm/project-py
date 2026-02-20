# User Requirements

## Target users

## Organization Owner
- Create the organization and manage membership.
- Override workflow rules when needed.

## Project Manager
- Create projects.
- Assign members.
- Archive tasks.

## Developer
- Execute assigned tasks and move work through the workflow.
- Log time and collaborate through review.

## Reviewer
- Review tasks and approve work in "In Review".

## Functional requirements
- Organization isolation for all reads/writes.
- Project membership enforcement.
- Task workflow state machine with role-restricted transitions.
- Review-gated completion (cannot complete without approval).
- Time logging per task with restrictions.
- Overdue detection.
- Audit log visibility.
- Analytics/performance dashboards.

## Non-functional requirements
- Security: strict org isolation, RBAC, object-level permissions.
- Reliability: transactional workflow transitions.
- Performance: efficient list endpoints and dashboard queries.
- Operability: production settings, Docker/Gunicorn, health checks.

## How the implementation satisfies the requirements
- Organization isolation: enforced by org scoping on queries.
- RBAC/workflow: enforced by `TaskWorkflowService` with atomic transitions.
- Time tracking: enforced by `TimeEntryService`.
- Audit + dashboards: audit middleware + dashboard views.
