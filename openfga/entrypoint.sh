#!/bin/sh
set -e

# Render's blueprint envVars can't interpolate other envVars into one
# composed value, so OPENFGA_DATASTORE_URI is built here instead, where
# normal shell ${VAR} expansion works. "$@" is whatever render.yaml's
# preDeployCommand/dockerCommand pass through (migrate / run), the same
# split docker-compose.yml uses for this image.
export OPENFGA_DATASTORE_URI="root:${MYSQL_ROOT_PASSWORD}@tcp(${MYSQL_HOST}:${MYSQL_PORT})/openfga?parseTime=true"
exec /openfga "$@"
