# Testing Plan

## Manual QA scenarios
- Login/logout flows.
- Create organization and project; verify only members can access.
- Create tasks and verify Kanban reflects workflow state.
- Attempt invalid transitions (e.g. complete without approval) should fail.
- Log time for a task; verify restrictions (negative time rejected; edit window enforced).
- Overdue: set deadline in the past; run overdue job; verify indicator.
- Audit dashboard: verify logs appear.
- Analytics/performance dashboards: verify metrics render.

## Automated testing

### Unit
- Service methods (workflow transitions, time entry restrictions, overdue marking).

### Integration
- API endpoints with JWT auth, org scoping, and DB assertions.

### Security
- Cross-organization access attempts.
- Privilege escalation attempts.

### Performance
- Basic evaluation endpoint timing checks (smoke-level) and query-count assertions.
