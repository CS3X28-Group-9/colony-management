#!/usr/bin/env bash
set -eux

cd mousemetrics
python manage.py migrate
python manage.py collectstatic --clear --no-input

if [ -n "${MOUSEMETRICS_ROOT_PASSWORD-}" ]; then
  python manage.py createsuperuser --username root --email "root@$MOUSEMETRICS_HOST" --no-input ||:
  # manage.py changepassword forces TTY user input for password
  python manage.py shell <<PASS
import os
root = User.objects.get(username='root')
root.set_password(os.environ["MOUSEMETRICS_ROOT_PASSWORD"])
root.save()
PASS
fi

if [ -n "${MOUSEMETRICS_LOAD_EXAMPLE_DATA}" ]; then
  python manage.py loaddata mice
fi

gunicorn mousemetrics.wsgi:application
