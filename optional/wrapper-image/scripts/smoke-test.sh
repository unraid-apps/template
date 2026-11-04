#!/usr/bin/env bash
# Generic smoke test: the container must stay up and answer on HEALTH_PATH.
# Extend it with checks for whatever your entrypoint does (files created,
# refusal on bad input, ...). Usage: smoke-test.sh <image>
set -euo pipefail
IMAGE="${1:?image required}"
PORT="${CONTAINER_PORT:-8080}"
HEALTH_PATH="${HEALTH_PATH:-/}"
NAME="smoke-$$"
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

docker run -d --name "$NAME" -p "127.0.0.1::$PORT" "$IMAGE" >/dev/null
host_port="$(docker port "$NAME" "$PORT/tcp" | head -1 | sed 's/.*://')"
deadline=$((SECONDS + 120))
until curl -fsS "http://127.0.0.1:${host_port}${HEALTH_PATH}" >/dev/null 2>&1; do
  docker ps -q --no-trunc --filter "name=^/${NAME}$" | grep -q . || { echo "container exited"; docker logs "$NAME" | tail -40; exit 1; }
  [ "$SECONDS" -lt "$deadline" ] || { echo "no answer on $HEALTH_PATH within 120s"; docker logs "$NAME" | tail -40; exit 1; }
  sleep 2
done
echo "SMOKE OK"
