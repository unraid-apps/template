#!/bin/sh
# Wrapper entrypoint skeleton. Do the one Unraid-specific thing here, then
# hand over to the upstream entrypoint unchanged. Never print secrets.
set -eu

UPSTREAM_ENTRYPOINT=/TODO/upstream/entrypoint   # from `docker inspect`; leave empty if upstream has none
log() { echo "unraid-entrypoint: $*" >&2; }

# Example: generate a secret on first start when the variable is empty.
# if [ -z "${APP_SECRET:-}" ]; then
#   FILE=/data/.app-secret
#   if [ ! -f "$FILE" ]; then
#     umask 077; od -An -N32 -tx1 /dev/urandom | tr -d ' \n' > "$FILE"
#     log "generated $FILE - back it up"
#   fi
#   APP_SECRET="$(cat "$FILE")"; export APP_SECRET
# fi

if [ -n "$UPSTREAM_ENTRYPOINT" ]; then
  [ -x "$UPSTREAM_ENTRYPOINT" ] || { log "ERROR: $UPSTREAM_ENTRYPOINT missing; upstream layout changed"; exit 1; }
  exec "$UPSTREAM_ENTRYPOINT" "$@"
fi
exec "$@"
