#!/bin/sh
set -e

# Render's blueprint envVars can't interpolate other envVars into one
# composed value, so the MySQL DSN is built here instead, where normal
# shell ${VAR} expansion works. Only do this when MySQL details were
# actually provided (render.yaml) - other datastore engines (e.g. sqlite,
# used by render.smoketest.yaml to avoid needing a paid private service)
# set OPENFGA_DATASTORE_URI directly via envVars instead.
if [ -n "$MYSQL_HOST" ]; then
  export OPENFGA_DATASTORE_URI="root:${MYSQL_ROOT_PASSWORD}@tcp(${MYSQL_HOST}:${MYSQL_PORT})/openfga?parseTime=true"
fi

# `openfga migrate` is safe to re-run against an already-migrated database,
# so running it here on every boot (instead of via a separate
# preDeployCommand) works everywhere, including Render's free plan, which
# doesn't support preDeployCommand at all.
if [ "$1" = "run" ]; then
  /openfga migrate
fi

exec /openfga "$@"
