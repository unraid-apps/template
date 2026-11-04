# syntax=docker/dockerfile:1.7
# Wrapper image skeleton: the upstream image plus an entrypoint of your own.
# Keep it to COPY instructions so the multi-arch build needs no emulation.
ARG UPSTREAM_IMAGE=ghcr.io/TODO-owner/TODO-image
ARG UPSTREAM_TAG=latest
FROM ${UPSTREAM_IMAGE}:${UPSTREAM_TAG}

ARG UPSTREAM_IMAGE
ARG UPSTREAM_TAG
ARG WRAPPER_REVISION=dev

LABEL org.opencontainers.image.title="APPNAME (Unraid wrapper)" \
      org.opencontainers.image.source="https://github.com/unraid-apps/APPNAME" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${UPSTREAM_TAG}" \
      org.opencontainers.image.base.name="${UPSTREAM_IMAGE}:${UPSTREAM_TAG}" \
      io.unraid-apps.wrapper.revision="${WRAPPER_REVISION}"

COPY --chmod=755 entrypoint.sh /usr/local/bin/unraid-entrypoint.sh

# TODO: match the upstream image. `docker inspect <image>` shows Entrypoint,
# Cmd and User. If upstream runs as root and drops privileges itself, keep
# USER root here; otherwise set the same USER as upstream.
USER root
ENTRYPOINT ["/usr/local/bin/unraid-entrypoint.sh"]
CMD ["TODO", "upstream", "cmd"]
