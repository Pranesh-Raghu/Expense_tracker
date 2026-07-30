# Render's blueprint spec doesn't support bind-mounting a repo file into a
# stock image the way docker-compose's `volumes:` does, so this wraps the
# official MySQL image just to bake in the same init script docker-compose
# mounts at ./mysql-init - it still only runs once, on an empty data
# directory, exactly like docker-entrypoint-initdb.d normally does.
FROM mysql:8.0
COPY mysql-init/ /docker-entrypoint-initdb.d/
