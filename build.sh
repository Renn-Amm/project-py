#!/usr/bin/env bash
set -o errexit

pip install -r requirements/prod.txt
pip install whitenoise

python manage.py collectstatic --no-input
python manage.py migrate
