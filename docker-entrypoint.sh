#!/bin/sh
set -e

# Composes env vars for Render deploys where render.yaml only has discrete
# pieces available (fromService gives host/port separately, and there's no
# way to interpolate one blueprint envVar into another). docker-compose.yml
# sets DATABASE_URL/OAUTH_ISSUER/OPENFGA_API_URL/CORS_ORIGINS directly
# already, so these defaults only kick in when that full value is unset.
#
# This used to be inlined as a `dockerCommand: sh -c '...'` string in
# render.yaml, but Render wraps dockerCommand in its own shell invocation,
# and the embedded single quotes collided with that wrapper. A real script
# baked into the image sidesteps the quoting entirely.

if [ -z "$DATABASE_URL" ] && [ -n "$MYSQL_HOST" ]; then
  DATABASE_URL="mysql+pymysql://root:${MYSQL_ROOT_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE:-expensetracker}"
fi
: "${DATABASE_URL:=sqlite:////tmp/expensetracker.db}"
: "${OAUTH_ISSUER:=$RENDER_EXTERNAL_URL}"

if [ -z "$OPENFGA_API_URL" ] && [ -n "$OPENFGA_HOST" ]; then
  OPENFGA_API_URL="http://${OPENFGA_HOST}:${OPENFGA_PORT}"
fi

if [ -z "$CORS_ORIGINS" ] && [ -n "$FRONTEND_HOST" ]; then
  CORS_ORIGINS="https://${FRONTEND_HOST}"
fi

export DATABASE_URL OAUTH_ISSUER OPENFGA_API_URL CORS_ORIGINS

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
