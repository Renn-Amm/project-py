# Future Improvements

## Feature roadmap
- Multi-tenant memberships and teams.
- Self-serve API keys and scoped evaluation credentials.
- Per-flag permissions and approval policies.

## Technical debt
- Increase mypy coverage and reduce `ignore_missing_imports`.
- Add query-count regression tests for N+1 prevention.

## Security improvements
- Add automated secret scanning enforcement.
- Add SAST tooling (bandit/semgrep) as optional CI job.

## Scalability improvements
- Redis caching for evaluation results with tenant+flag+user key.
- Async ingestion for analytics events.
