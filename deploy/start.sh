#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py seed_kyc
python manage.py collectstatic --noinput

gunicorn playto_kyc.wsgi:application --bind "0.0.0.0:${PORT:-10000}"

