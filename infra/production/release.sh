#!/usr/bin/env sh
set -eu

# Run database migrations as a one-shot release step.
# Service readiness is verified by the API/container healthcheck after startup.
python -m alembic upgrade head

echo 'Production database migrations completed.'
