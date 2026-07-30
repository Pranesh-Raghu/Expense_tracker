# openfga/openfga is a shell-less/distroless-style image (no /bin/sh) -
# earlier attempts at a shell entrypoint failed at build time
# ("exec: /bin/sh: no such file"), and exec-form RUN could only bake a
# *static, build-time-known* config (e.g. a fixed sqlite path), not
# anything depending on a runtime secret (a real Postgres/MySQL URI).
#
# Copying a static busybox binary in from another image (multi-stage,
# no shared base needed) gives this image a real shell without needing
# openfga/openfga itself to have one. Not placed at /bin/sh: the image
# runs as a non-root user with no write access to /bin, so it lives at
# /busybox instead and is invoked directly as the ENTRYPOINT.
FROM busybox:musl AS shell
FROM openfga/openfga:latest
COPY --from=shell /bin/busybox /busybox
ENTRYPOINT ["/busybox", "sh", "-c"]

# Composes OPENFGA_DATASTORE_URI from MYSQL_HOST/PORT/MYSQL_ROOT_PASSWORD
# when those are present (render.yaml's real MySQL setup, where Render's
# fromService only hands over discrete host/port/password - there's no
# way to interpolate one blueprint envVar into another). Otherwise trusts
# OPENFGA_DATASTORE_ENGINE/OPENFGA_DATASTORE_URI as given directly - e.g.
# render.smoketest.yaml pointing at a free external Postgres (Neon),
# needed for real persistence: Render's free plan doesn't support
# persistent disks at all, so no local sqlite file survives a redeploy.
#
# `openfga migrate` is safe to re-run against an already-migrated
# database, so running it on every boot (there's no preDeployCommand on
# Render's free plan, and one-off Jobs are paid-only) works everywhere.
CMD ["if [ -n \"$MYSQL_HOST\" ]; then export OPENFGA_DATASTORE_ENGINE=mysql; export OPENFGA_DATASTORE_URI=\"root:${MYSQL_ROOT_PASSWORD}@tcp(${MYSQL_HOST}:${MYSQL_PORT})/openfga?parseTime=true\"; fi; /openfga migrate --datastore-engine \"$OPENFGA_DATASTORE_ENGINE\" --datastore-uri \"$OPENFGA_DATASTORE_URI\" && exec /openfga run"]
