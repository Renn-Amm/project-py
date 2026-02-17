# Feature Flag Management System

A production-grade, multi-tenant SaaS Feature Flag Management System built with Django and Django REST Framework.

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
│   ├── tenants/               # Tenant model, environments, middleware
│   ├── feature_flags/         # Flags, variants, evaluation engine
│   ├── targeting/             # Targeting rules, operators
│   ├── policies/              # Policy engine, approval workflow
│   ├── audit/                 # Audit logging, middleware
│   ├── analytics/             # Evaluation events, analytics
│   ├── core/                  # Health check, exception handler
│   └── dashboard/             # Admin dashboard (Django templates)
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

- **Multi-tenant isolation** — All queries scoped by tenant; middleware rejects orphaned users
- **Multi-environment** — development, staging, production per tenant
- **Advanced targeting** — User ID, role, country, email, custom attributes with 11 operators
- **Percentage rollout** — Deterministic hashing (SHA-256) for consistent user assignment
- **Experiment mode** — A/B testing with control/treatment variants
- **Time-based activation** — Schedule flag activation and auto-expiration
- **Flag dependencies** — Child flags auto-disable when parent is off
- **Kill switch** — Instant emergency disable
- **Approval workflow** — High/critical risk production flags require admin approval
- **Policy engine** — Configurable rules (key immutability, production-owner-only, etc.)
- **Audit logging** — Automatic middleware-based logging of all mutations
- **Analytics** — Evaluation tracking, variant distribution, experiment results
- **Stale flag detection** — Flags not evaluated in N days flagged for cleanup
- **Role-based access control** — Owner > Admin > Developer > Viewer hierarchy

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
| `STALE_FLAG_DAYS`     | No       | 30                       | Days before flag marked stale  |
| `EVALUATION_CACHE_TTL`| No       | 60                       | Cache TTL in seconds           |

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

### Feature Flags
| Method | Endpoint                        | Description            |
|--------|---------------------------------|------------------------|
| GET    | `/api/flags/`                   | List flags (filtered)  |
| POST   | `/api/flags/create/`            | Create flag            |
| GET    | `/api/flags/<id>/`              | Flag detail            |
| PATCH  | `/api/flags/<id>/`              | Update flag            |
| DELETE | `/api/flags/<id>/`              | Delete flag            |
| POST   | `/api/flags/<id>/toggle/`       | Toggle enabled state   |
| POST   | `/api/flags/<id>/variants/`     | Set variants           |
| POST   | `/api/flags/<id>/archive/`      | Archive flag           |
| POST   | `/api/flags/<id>/kill-switch/`  | Activate/deactivate    |
| GET    | `/api/flags/stale/`             | List stale flags       |

### Evaluation (SDK Endpoint)
| Method | Endpoint          | Description                |
|--------|-------------------|----------------------------|
| POST   | `/api/evaluate/`  | Evaluate flag for user     |

**Headers:** `X-Tenant-Slug: <tenant-slug>`

**Request:**
```json
{
  "flag_key": "new-checkout",
  "user_identifier": "user-123",
  "environment": "production",
  "attributes": {"country": "US", "plan": "enterprise"}
}
```

**Response:**
```json
{
  "variant": {"checkout_v2": true},
  "reason": "targeting_rule_match",
  "rule_matched": null
}
```

### Targeting Rules
| Method | Endpoint                              | Description       |
|--------|---------------------------------------|--------------------|
| GET    | `/api/targeting/flags/<id>/rules/`    | List rules for flag|
| POST   | `/api/targeting/rules/`               | Create rule        |
| PATCH  | `/api/targeting/rules/<id>/`          | Update rule        |
| DELETE | `/api/targeting/rules/<id>/`          | Delete rule        |

### Policies & Approvals
| Method | Endpoint                                  | Description          |
|--------|-------------------------------------------|----------------------|
| GET    | `/api/policies/`                          | List policies        |
| POST   | `/api/policies/<id>/toggle/`              | Toggle policy        |
| GET    | `/api/policies/approvals/`                | Approval queue       |
| POST   | `/api/policies/approvals/create/`         | Request approval     |
| POST   | `/api/policies/approvals/<id>/approve/`   | Approve request      |
| POST   | `/api/policies/approvals/<id>/reject/`    | Reject request       |

### Audit & Analytics
| Method | Endpoint                                       | Description           |
|--------|------------------------------------------------|-----------------------|
| GET    | `/api/audit/logs/`                             | List audit logs       |
| GET    | `/api/audit/logs/<type>/<id>/`                 | Object audit history  |
| GET    | `/api/analytics/summary/`                      | Tenant analytics      |
| GET    | `/api/analytics/flags/<id>/`                   | Flag analytics        |
| GET    | `/api/analytics/experiments/<id>/`             | Experiment results    |

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
| Flag key unique per tenant+environment        | DB unique_together + service |
| Variant percentages sum to 100                | Service layer validation |
| Cannot modify archived flags                  | Model clean + service    |
| Cannot enable flag with kill switch active    | Service layer            |
| Production high-risk flags require approval   | Service + policy engine  |
| Cannot delete flag with active dependents     | Service layer            |
| Key immutable after creation                  | Service + policy engine  |
| Tenant isolation on all queries               | Middleware + view layer  |
| Role-based access on all endpoints            | Permission classes       |
| Cannot approve own request                    | Service layer            |
| Expired flags auto-deactivate                 | Service layer            |
| Dependencies must be same environment         | Model validation         |
| Self-dependency rejected                      | Model validation         |

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
DJANGO_ENV=test pytest tests/test_feature_flags.py

# Specific test class
DJANGO_ENV=test pytest tests/test_tenant_isolation.py::TestCrossTenantFlagAccess
```

## CI Pipeline

GitHub Actions runs on every push to `main`/`develop` and all PRs:

1. **Lint** — `ruff check`
2. **Test** — `pytest` with PostgreSQL service container
3. **Coverage** — Fails if below 80%
4. **Security** — `pip-audit --strict` for dependency vulnerabilities
5. **Docker** — Build and verify image (main branch only)
