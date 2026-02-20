# TaskFlow

TaskFlow is a multi-tenant team task and performance management system built with Django. It provides organization-scoped project management, sprint planning, task workflows with review gates, time tracking, performance analytics, and a full audit trail.

## Features

### Authentication & Organization
- Sign up creates an organization + owner account
- JWT-based API authentication with token rotation
- Session-based dashboard login
- Token-based team invitations (48h expiry, single-use)
- 5 roles: Owner, Project Manager, Developer, Reviewer, Viewer

### Project & Task Management
- Organization-scoped projects with membership enforcement
- Kanban-style task board with 7 statuses: Backlog → In Progress → On Hold → In Review → Approved → Completed → Archived
- Backend-enforced workflow transitions (e.g., only reviewer can approve, completion requires review)
- Task priorities: Low, Medium, High, Critical (with weighted scoring)
- Task dependencies with circular dependency detection
- Sprint planning with goals, start/end dates, and auto-close

### Time Tracking
- Per-task time entries with daily granularity
- Immutable entries after 24-hour edit window
- Negative time validation at the service layer

### Performance Analytics
- Weighted performance scoring: completion rate, overdue rate, rejection rate, time accuracy
- Team leaderboard by hours logged
- Weekly analytics: completed tasks, hours, overdue counts, status breakdown
- 30-day performance metrics

### Notifications & Activity Feed
- Smart notifications: task assignments, review requests, rejections, overdue alerts
- Mark read / mark all read
- Immutable activity feed (append-only audit trail)
- Activity types: status change, time logged, review submitted, assignment changed, task created

### Audit & Security
- Middleware-driven mutation logging for all API actions
- Organization-scoped immutable audit log
- Zero cross-tenant data leaks enforced at every layer

### Dashboard
- Premium dark/light mode UI with Inter font
- Landing page with feature showcase
- Kanban board with color-coded status columns
- Performance metrics with leaderboard
- Analytics with status breakdown bars
- Audit log table with action badges
- Invitation management (send, view status)
- Notification center with unread indicators
- Activity feed timeline

## Tech Stack

- **Backend:** Python 3.11 + Django 4.2 LTS + Django REST Framework
- **Frontend:** Server-rendered templates, Tailwind CSS (CDN), Alpine.js, HTMX
- **Database:** PostgreSQL via `DATABASE_URL`
- **Static Files:** WhiteNoise (compressed + cache-busted)
- **Server:** Gunicorn (production)
- **Infrastructure:** Docker + docker-compose, Render (free tier)
- **Quality:** ruff, mypy, pre-commit, pytest (≥80% coverage)
- **CI/CD:** GitHub Actions (lint, typecheck, migrations check, tests, coverage, pip-audit)

## Project Structure

```
.
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── local.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/         # User model, Invitation model, JWT views
│   ├── organizations/    # Organization model
│   ├── projects/         # Project, ProjectMember, Sprint models
│   ├── tasks/            # Task, TaskDependency, TaskStatusChange models
│   ├── time_tracking/    # TimeEntry model and service
│   ├── notifications/    # Notification model
│   ├── performance/      # Performance scoring engine
│   ├── audit/            # AuditLog, ActivityEntry models
│   ├── core/             # Health check, landing page, signup views
│   └── dashboard/        # Server-rendered dashboard views
├── templates/
│   ├── base.html
│   ├── public/           # Landing page, signup
│   ├── dashboard/        # All dashboard pages
│   └── partials/         # Sidebar, topbar
├── tests/
├── requirements/
│   ├── prod.in / prod.txt
│   └── dev.in / dev.txt
├── render.yaml             # Render blueprint
├── build.sh                # Render build script
└── .github/
    └── workflows/
        ├── ci.yml
        └── cd.yml
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | JWT login |
| POST | `/api/auth/token/refresh/` | Refresh JWT |
| POST | `/api/auth/logout/` | Blacklist token |
| GET | `/api/auth/me/` | Current user profile |

### Projects & Sprints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/projects/` | List/create projects |
| GET/PUT/DELETE | `/api/projects/{id}/` | Project CRUD |
| GET/POST | `/api/sprints/` | List/create sprints |
| GET/PUT/DELETE | `/api/sprints/{id}/` | Sprint CRUD |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/tasks/` | List/create tasks |
| GET/PUT/DELETE | `/api/tasks/{id}/` | Task CRUD |
| POST | `/api/tasks/{id}/transition/` | Status transition |
| GET/POST | `/api/tasks/{id}/dependencies/` | Manage dependencies |

### Time Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/time-entries/` | List/create time entries |

### Performance
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/performance/score/` | User performance score |
| GET | `/api/performance/team/` | Team leaderboard |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List notifications |
| POST | `/api/notifications/{id}/read/` | Mark as read |

### Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/audit/logs/` | Audit log (admin) |
| GET | `/api/audit/activity/` | Activity feed |

### Invitations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/invitations/` | Create invitation |
| POST | `/api/invitations/accept/` | Accept invitation |

## Local Setup

```bash
python -m venv .venv
. .venv/Scripts/activate       # Windows: .venv\Scripts\activate

pip install -r requirements/dev.txt

python manage.py migrate
python manage.py runserver
```

Or with Docker:

```bash
docker-compose up --build
```

## Dependency Management

```bash
pip install pip-tools

# Lock without upgrading
pip-compile requirements/prod.in --generate-hashes -o requirements/prod.txt
pip-compile requirements/dev.in --generate-hashes -o requirements/dev.txt

# Upgrade all
pip-compile --upgrade requirements/prod.in --generate-hashes -o requirements/prod.txt
pip-compile --upgrade requirements/dev.in --generate-hashes -o requirements/dev.txt
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Production | Django secret key |
| `ALLOWED_HOSTS` | Production | Comma-separated hosts (e.g. `.onrender.com`) |
| `DATABASE_URL` | Always | PostgreSQL connection string |
| `DJANGO_ENV` | Optional | development / production / test |
| `DJANGO_SETTINGS_MODULE` | Optional | `config.settings` (default) |
| `PYTHON_VERSION` | Render | `3.11.14` |
| `CORS_ALLOWED_ORIGINS` | Optional | CORS whitelist |
| `REDIS_URL` | Optional | Redis URL (falls back to in-memory cache) |
| `DB_SSLMODE` | Optional | e.g. `require` for SSL-enabled Postgres |

## Quality and Checks

```bash
ruff check apps config tests        # Linting
mypy                                 # Type checking
python manage.py makemigrations --check --dry-run   # Migration drift
pytest                               # Tests + coverage (≥80%)
pip-audit --strict --desc            # Security scan
```

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs:
- Dependency install
- ruff lint
- mypy type check
- Migration drift check
- pytest + coverage (≥ 80%)
- pip-audit (`--strict`)
- Docker build

## Render Deployment (Free Tier)

### Option A: Blueprint (recommended)
1. Push to GitHub
2. Render → **New → Blueprint** → connect repo → it reads `render.yaml`
3. Wait ~3-5 min for build

### Option B: Manual
1. Create **Postgres** (free plan) on Render
2. Create **Web Service** → connect repo
3. Set Build Command: `./build.sh`
4. Set Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
5. Add env vars (see table below)

### After deploy
```bash
# Via Render Shell tab:
python manage.py createsuperuser
```

Production runs behind Gunicorn with WhiteNoise for static files.
