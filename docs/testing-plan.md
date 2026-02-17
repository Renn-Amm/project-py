# Testing Plan

## Manual QA scenarios
- Login/logout flows.
- Create flag in dev/staging; verify visibility for tenant only.
- Configure variants for multivariate/experiment; validate percentages sum to 100.
- Add/delete targeting rules and verify ordering/priority.
- Attempt cross-tenant access via API (should be 404/403).
- Production high-risk flag modification should require approval.
- Approval queue: approve/reject with reason; verify state changes.
- Kill switch: activate disables flag immediately.
- Analytics dashboard: verify counts and charts render.

## Automated testing

### Unit
- Service methods (variant validation, toggles, approvals, policy checks).

### Integration
- API endpoints with JWT auth, tenant scoping, and DB assertions.

### Security
- Cross-tenant access attempts.
- Privilege escalation attempts.
- Unauthorized production modifications.

### Performance
- Basic evaluation endpoint timing checks (smoke-level) and query-count assertions.
