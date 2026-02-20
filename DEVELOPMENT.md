# Development Guide

## Local setup

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements/dev.txt
```

### 3) Run database + app (Docker)

```bash
docker-compose up -d
```

### 4) Run tests

```bash
DJANGO_ENV=test pytest
```

### 5) Run linters / type checks

```bash
ruff check apps config tests
mypy apps config
```

## Pre-commit

### Install hooks

```bash
pre-commit install
```

### Run on all files

```bash
pre-commit run --all-files
```

## Local workflow

- Keep changes small and covered by tests.
- Run `pre-commit` before pushing.
- Use `DJANGO_ENV=test` for test runs.

## Dependency updates

- Production dependencies: `requirements/prod.txt`
- Development dependencies: `requirements/dev.txt`
- `requirements.txt` is a compatibility shim that includes `requirements/dev.txt`.

### Regenerate lock files (pip-tools)

```bash
pip-compile requirements/prod.in -o requirements/prod.txt --generate-hashes --allow-unsafe
pip-compile requirements/dev.in -o requirements/dev.txt --generate-hashes --allow-unsafe
```

## Windows pre-push checklist

```bash
ruff check apps config tests
mypy apps config
DJANGO_ENV=test pytest
python manage.py makemigrations --check --dry-run
docker build -t task-manager:local .
```
