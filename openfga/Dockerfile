# Wraps the stock OpenFGA image so preDeployCommand/dockerCommand in
# render.yaml can pass just "migrate"/"run" as args (mirroring
# docker-compose.yml's `command:` for this same image) without depending on
# whether Render's dockerCommand override replaces the base image's own
# ENTRYPOINT or only its CMD.
FROM openfga/openfga:latest
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["run"]
