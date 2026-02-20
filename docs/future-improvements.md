# Future Improvements

## Feature roadmap
- Multi-organization memberships and teams.
- More workflow states and per-project policies.
- Expanded analytics and reporting exports.

## Technical debt
- Increase mypy coverage and reduce `ignore_missing_imports`.
- Add query-count regression tests for N+1 prevention.

## Security improvements
- Add automated secret scanning enforcement.
- Add SAST tooling (bandit/semgrep) as optional CI job.

## Scalability improvements
- Redis caching for dashboard aggregations.
- Async ingestion for audit/analytics events.
