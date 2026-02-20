# Task Manager

A production-grade, organization-isolated Task Management system built with Django and Django REST Framework.

## Architecture

```
project/
├── config/                    # Django configuration
│   ├── settings/
│   │   ├── __init__.py        # Environment-based settings selector
│   │   ├── base.py            # Shared settings
│   │   ├── development.py     # Dev overrides (DEBUG=True)
│   │   ├── production.py      # Production hardening (SSL, HSTS, etc.)
│   │   └── test.py            # Test overrides (fast hashing, no throttle)
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/              # User model, JWT auth, RBAC
│   ├── organizations/         # Organization model
│   ├── projects/              # Projects + membership
│   ├── tasks/                 # Tasks + workflow state machine
│   ├── time_tracking/         # Time entries (restricted edits)
│   ├── audit/                 # Audit logging, middleware
│   ├── performance/           # Performance app placeholder
│   ├── core/                  # Health check, exception handler
│   └── dashboard/             # Server-rendered dashboard (Django templates)
├── tests/                     # Comprehensive test suite
├── templates/                 # Dashboard HTML templates
├── .github/workflows/ci.yml   # CI pipeline
├── Dockerfile                 # Multi-stage production build
├── docker-compose.yml         # Local development
└── requirements.txt           # Pinned dependencies
```

## Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.11+                        |
| Framework       | Django 4.2, Django REST Framework   |
| Database        | PostgreSQL 15                       |
| Authentication  | JWT (SimpleJWT) with token blacklist|
| Testing         | pytest, pytest-django, pytest-cov   |
| Linting         | ruff                                |
| Security Scan   | pip-audit                           |
| CI              | GitHub Actions                      |
| Container       | Docker (multi-stage build)          |

## Key Features

- **Organization isolation** — All reads/writes are scoped to `user.organization`
- **Project membership enforcement** — Only members can view/change a project
- **Workflow state machine** — Backend-enforced transitions + role restrictions
- **Review-gated completion** — Cannot complete a task without reviewer approval
- **Overdue detection** — Scheduled management command marks overdue tasks
- **Time tracking** — Log time per task; restricted editing rules
- **Audit logging** — Tracks status changes and important mutations
- **Analytics** — Dashboard metrics for throughput/time
- **Role-based access control** — Owner > Project Manager > Developer > Viewer

## Quick Start

```bash
# Clone and start
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run tests
docker-compose exec web pytest
```

## Environment Variables

| Variable              | Required | Default                  | Description                    |
|-----------------------|----------|--------------------------|--------------------------------|
| `SECRET_KEY`          | Yes (prod) | dev key                | Django secret key              |
| `DJANGO_ENV`          | No       | development              | development / production / test|
| `DATABASE_URL`        | No       | postgres://...localhost  | PostgreSQL connection string   |
| `ALLOWED_HOSTS`       | Yes (prod) | *                      | Comma-separated hostnames      |
| `CORS_ALLOWED_ORIGINS`| Yes (prod) |                        | Comma-separated origins        |
| `REDIS_URL`           | No       | redis://localhost:6379/0 | Redis for caching (prod)       |

## API Endpoints

### Authentication
| Method | Endpoint                  | Description          |
|--------|---------------------------|----------------------|
| POST   | `/api/auth/register/`     | Register new user    |
| POST   | `/api/auth/login/`        | Obtain JWT tokens    |
| POST   | `/api/auth/refresh/`      | Refresh access token |
| POST   | `/api/auth/logout/`       | Blacklist refresh token |
| GET    | `/api/auth/profile/`      | Get current user     |
| POST   | `/api/auth/change-password/` | Change password   |

### Projects
| Method | Endpoint                     | Description           |
|--------|------------------------------|-----------------------|
| GET    | `/api/projects/`             | List projects         |
| POST   | `/api/projects/`             | Create project        |
| GET    | `/api/projects/<id>/`        | Project detail        |
| PATCH  | `/api/projects/<id>/`        | Update project        |

### Tasks
| Method | Endpoint                                   | Description                 |
|--------|--------------------------------------------|-----------------------------|
| GET    | `/api/tasks/`                               | List tasks (filters)        |
| POST   | `/api/projects/<project_id>/tasks/`         | Create task                 |
| GET    | `/api/tasks/<id>/`                          | Task detail                 |
| POST   | `/api/tasks/<id>/transition/`               | Workflow transition         |
| POST   | `/api/tasks/<id>/time-entries/`             | Log time for task           |

### Audit
| Method | Endpoint                | Description     |
|--------|-------------------------|-----------------|
| GET    | `/api/audit/logs/`      | List audit logs |

### Health
| Method | Endpoint          | Description       |
|--------|-------------------|--------------------|
| GET    | `/api/health/`    | Health check       |

## Ruleset Protection Strategy

All business rules enforced at **three layers**:

1. **Model validation** (`clean()` + `save()` override) — Prevents invalid state at ORM level
2. **Service layer** — Business logic with `@transaction.atomic` and `select_for_update()`
3. **Database constraints** — `unique_together`, foreign keys, check constraints

### Critical Rules Enforced

| Rule                                          | Enforcement Layer        |
|-----------------------------------------------|--------------------------|
| Organization isolation on all queries         | View/service scoping     |
| Role-restricted task transitions              | Service layer            |
| Cannot complete without review approval       | Service layer            |
| Overdue detection not removable manually      | Model/service + cron cmd |
| Time entry edit restrictions                  | Service layer            |

## Backup & Recovery Strategy

### Database Backups
- **Frequency:** Daily full backup + continuous WAL archiving
- **Retention:** 30 days of daily backups, 7 days of WAL
- **Method:** `pg_dump` for logical backups, WAL-G for continuous archiving
- **Storage:** Encrypted S3 bucket in separate region

### Restore Testing
- Monthly restore drill to staging environment
- Automated restore verification in CI (quarterly)

### Disaster Recovery
- **RPO (Recovery Point Objective):** < 5 minutes (WAL archiving)
- **RTO (Recovery Time Objective):** < 30 minutes
- **Procedure:** Restore from latest WAL archive → verify data integrity → switch DNS

## Running Tests

```bash
# Full test suite with coverage
DJANGO_ENV=test pytest

# Specific test file
DJANGO_ENV=test pytest tests/test_overdue_job.py
```

## CI Pipeline

GitHub Actions runs on every push to `main`/`develop` and all PRs:

1. **Lint** — `ruff check`
2. **Test** — `pytest` with PostgreSQL service container
3. **Coverage** — Fails if below 80%
4. **Security** — `pip-audit --strict` for dependency vulnerabilities
5. **Docker** — Build and verify image (main branch only)
