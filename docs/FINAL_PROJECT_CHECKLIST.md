# TaskFlow — Final Project Checklist

## 1. User Requirements

### Target Users
- **Team leads / Project managers** who need to coordinate multi-person software projects
- **Developers** who need clear task assignments, status tracking, and time logging
- **Organization owners** who want visibility into team performance and audit trails

### Functional Requirements
| # | Requirement | Status |
|---|---|---|
| F1 | User registration & login (JWT + session-based) | ✅ Implemented |
| F2 | Multi-tenant organization isolation | ✅ Implemented |
| F3 | Role-based access control (Owner, PM, Developer, Reviewer, Viewer) | ✅ Implemented |
| F4 | Project CRUD with team membership management | ✅ Implemented |
| F5 | Task lifecycle with workflow-enforced status transitions | ✅ Implemented |
| F6 | Time tracking per task with per-user logging | ✅ Implemented |
| F7 | Performance analytics (hours logged, completion rate, overdue tracking) | ✅ Implemented |
| F8 | Audit log of all significant actions | ✅ Implemented |
| F9 | Invitation system for adding users to an organization | ✅ Implemented |
| F10 | Real-time activity feed | ✅ Implemented |
| F11 | Notification system | ✅ Implemented |

### Non-Functional Requirements
| # | Requirement | Status |
|---|---|---|
| NF1 | Password minimum 10 chars with Django validators | ✅ |
| NF2 | CSRF protection on all forms | ✅ |
| NF3 | Rate limiting (anon: 30/min, user: 500/min in prod) | ✅ |
| NF4 | HTTPS enforcement + HSTS headers in production | ✅ |
| NF5 | Tenant data isolation (no cross-org data leaks) | ✅ Tested |
| NF6 | 80%+ test coverage | ✅ 85% |

### How The Product Satisfies Requirements
The dashboard provides a single-page-app-like experience where authenticated users can manage projects, tasks, team members, and track time — all scoped to their organization. The REST API enables future mobile or third-party integrations. Workflow enforcement prevents tasks from skipping status steps (e.g., can't go from Backlog directly to Completed).

---

## 2. Testing Plan

### Manual QA Scenarios
| # | Scenario | Steps |
|---|---|---|
| 1 | New user signup flow | Visit /signup → enter org name, email, password → verify redirect to dashboard |
| 2 | Project creation | Login → Projects → Create Project → verify it appears in list |
| 3 | Task lifecycle | Create task → transition through Backlog → In Progress → In Review → Approved → Completed |
| 4 | Time logging | Open task → log 2 hours → verify it shows in Performance page |
| 5 | Member management | Project detail → add member by email → verify they appear → remove them |
| 6 | Invitation flow | Invitations page → send invite → verify it appears in list |
| 7 | Cross-tenant isolation | Login as Org A user → try to access Org B project URL → verify 404 |
| 8 | Role enforcement | Login as Viewer → try to add member → verify rejection |

### Automated Tests
- **Framework**: pytest + pytest-django
- **Coverage**: 85%+ (76 tests across 12 test modules)
- **Test types used**:
  - Unit tests (model validation, service logic)
  - Integration tests (API endpoints, form submissions)
  - Security tests (RBAC, tenant isolation)
  - Dashboard page load tests (renders without 500 errors)
- **Run command**: `python -m pytest -v`

---

## 3. Technical Decisions

### Stack
| Layer | Technology | Why |
|---|---|---|
| Backend | Django 5 + DRF | Mature, batteries-included, strong ORM for multi-tenant patterns |
| Database | PostgreSQL | ACID compliance, good JSON support, free on Render |
| Auth | JWT (API) + Django sessions (dashboard) | JWT for stateless API, sessions for SSR dashboard |
| Frontend | Django templates + Tailwind CDN + Alpine.js + HTMX | No separate frontend build step; fast SSR with progressive enhancement |
| Deployment | Render (free tier) | Zero-config deploy with Blueprint, free Postgres included |
| Static files | WhiteNoise | Serves static files from Django directly, no separate nginx needed |

### Architecture Overview
```
┌─────────────────┐     ┌──────────────────┐
│  Browser / API  │────▶│  Django (Gunicorn)│
│   clients       │     │                  │
└─────────────────┘     │  ┌── REST API    │
                        │  │   (DRF + JWT)  │
                        │  ├── Dashboard    │
                        │  │   (Templates)  │
                        │  └── Admin        │
                        │                  │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │   PostgreSQL     │
                        │  (Render free)   │
                        └──────────────────┘
```

**App modules**: `accounts`, `organizations`, `projects`, `tasks`, `time_tracking`, `performance`, `audit`, `notifications`, `dashboard`, `core`

### Key Design Decisions
1. **Multi-tenant via FK** — Every model links to Organization via ForeignKey. Simple, works at our scale, avoids schema-per-tenant complexity.
2. **Workflow service pattern** — Task transitions go through `TaskWorkflowService` instead of raw status updates. This enforces valid transitions and auto-sets `completed_at`.
3. **Dual auth** — API uses JWT for stateless mobile/integration clients; dashboard uses Django sessions for cookie-based SSR.
4. **No JavaScript build step** — Tailwind CDN + Alpine.js + HTMX keeps the frontend simple (no webpack/vite/node).

### Trade-offs Considered
| Decision | Upside | Downside |
|---|---|---|
| Tailwind CDN vs. build | No build step, fast deploy | Larger CSS payload, no purging |
| Django monolith vs. microservices | Simple deployment, fast dev | Harder to scale individual features |
| Session auth for dashboard | No token storage in JS | Not RESTful, tied to cookies |
| WhiteNoise vs. CDN/S3 | Zero config | No edge caching, slower for global users |

---

## 4. Assumptions and Constraints

### Assumptions
- Teams are small-to-medium (< 50 members per organization)
- One user belongs to exactly one organization
- English-only UI is acceptable
- The Render free tier's 15-minute sleep is acceptable for demo purposes

### Simplifications
- No real email sending (invitations are stored in DB but not emailed)
- No file attachments on tasks
- No real-time push notifications (notification page is poll-based)
- No password reset flow (admin can do it via Django admin)

### Known Limitations
- Render free tier spins down after 15 min idle (~30 second cold start)
- No full-text search on tasks (basic Django ORM queries only)
- No drag-and-drop on the Kanban board (status changes via task detail page)
- Time entries cannot be edited after creation

### Postponed Requirements
- Email delivery for invitations and notifications
- File attachments
- Sprint/iteration management (model exists but UI is not built)
- Mobile-responsive optimizations for small screens
- Two-factor authentication

---

## 5. Future Improvements

### Next Features
1. Email delivery for invitations and password reset
2. Drag-and-drop Kanban board with HTMX
3. Sprint/iteration UI (model is already in the database)
4. Task comments and activity discussion thread
5. Dashboard export to CSV/PDF

### Technical Debt
- Move Tailwind from CDN to a proper build step (smaller bundles, purging)
- Add type hints to all view functions
- Split `task_views.py` (530+ lines) into smaller view modules
- Add database indexes for common query patterns
- Implement proper pagination on large lists

### Security Improvements
- Add two-factor authentication (TOTP)
- Implement password reset via email
- Add rate limiting on login endpoint specifically
- Add Content-Security-Policy headers
- Implement session timeout / forced re-auth for sensitive actions
