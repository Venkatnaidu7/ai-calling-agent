#!/usr/bin/env sh
set -eu

# Run this script inside the production API image/service network.
# The application must be stopped or drained before destructive migrations.
python -m alembic upgrade head
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')"
echo 'Production release migration and readiness check completed.'
