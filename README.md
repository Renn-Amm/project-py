# Task Manager

Task Manager is a Django web application for organization-scoped project and task management, including dashboards, workflow transitions, time tracking, and audit logging.

## Features

Authentication:

- Sign up, sign in, sign out (JWT + dashboard login)

Organization-scoped project management:

- Projects
- Membership enforcement

Task management:

- Kanban-style statuses and backend-enforced workflow transitions
- Review-gated completion rules
- Overdue detection via management command

Time tracking:

- Time entries per task
- Restricted edits (immutability window)

Audit logging:

- Middleware-driven mutation logging for key API actions
- Organization-scoped audit trail

Dashboard:

- Entity counts
- Performance metrics pages
- Audit log view

## Tech Stack

- Python + Django 4.2 LTS
- Django REST Framework
- Server-rendered templates for the dashboard
- Gunicorn (production)
- PostgreSQL via `DATABASE_URL`
- Docker + docker-compose for local development
- Quality tooling: ruff + mypy + pre-commit
- CI: GitHub Actions (lint, typecheck, migrations check, tests, coverage, pip-audit)

## Project Structure

```
.
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── organizations/
│   ├── projects/
│   ├── tasks/
│   ├── time_tracking/
│   ├── audit/
│   ├── core/
│   └── dashboard/
├── templates/
├── tests/
├── requirements/
│   ├── prod.in
│   ├── prod.txt
│   ├── dev.in
│   └── dev.txt
└── .github/
    └── workflows/
        ├── ci.yml
        └── cd.yml
```

## Local Setup

Create and activate a virtual environment.

Install dependencies.

Run migrations.

Start the server.

```bash
python -m venv .venv
. .venv/Scripts/activate

pip install -r requirements/dev.txt

python manage.py migrate
python manage.py runserver
```

## Dependency Management

Install pip-tools once in your active virtualenv:

```bash
pip install pip-tools
```

Direct dependencies live in:

- `requirements/prod.in`
- `requirements/dev.in`

Lock files consumed by CI/local installs:

- `requirements/prod.txt`
- `requirements/dev.txt`

Regenerate lock files without upgrading versions:

```bash
pip-compile requirements/prod.in --generate-hashes -o requirements/prod.txt
pip-compile requirements/dev.in --generate-hashes -o requirements/dev.txt
```

Upgrade all dependencies and refresh lock files:

```bash
pip-compile --upgrade requirements/prod.in --generate-hashes -o requirements/prod.txt
pip-compile --upgrade requirements/dev.in --generate-hashes -o requirements/dev.txt
```

Upgrade a single dependency and refresh lock files:

```bash
pip-compile --upgrade-package Django requirements/prod.in --generate-hashes -o requirements/prod.txt
pip-compile --upgrade-package Django requirements/dev.in --generate-hashes -o requirements/dev.txt
```

## Environment Variables

Required in production:

- `SECRET_KEY`
- `ALLOWED_HOSTS`

Database configuration:

- `DATABASE_URL`

Other useful variables:

- `DJANGO_ENV` (development/production/test)
- `CORS_ALLOWED_ORIGINS`
- `REDIS_URL` (if you enable Redis-backed caching)

Example:

```bash
export DATABASE_URL='postgresql://user:password@host/dbname?sslmode=require'
```

## Quality and Checks

Ruff:

```bash
ruff check apps config tests
```

mypy:

```bash
mypy
```

Django migration drift check:

```bash
python manage.py makemigrations --check --dry-run
```

Run tests (with coverage gate):

```bash
pytest --cov=apps --cov-report=term-missing --cov-fail-under=80
```

Security scan:

```bash
pip-audit --strict --desc
```

## Pre-commit

Install git hooks:

```bash
pre-commit install
```

Run all hooks manually:

```bash
pre-commit run --all-files
```

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs:

- Dependency install
- ruff lint
- mypy type check
- Migration drift check
- pytest + coverage (>= 80%)
- pip-audit (`--strict`)
- Docker build (as configured)

## Deployment

Production runs behind Gunicorn (see `Dockerfile` and deployment workflow).

For production, define environment variables in your platform instead of relying on local `.env` files.
