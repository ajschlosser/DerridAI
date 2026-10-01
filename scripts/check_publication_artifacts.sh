#!/bin/sh
set -eu

FIXTURE_DIR=${1:?usage: check_publication_artifacts.sh FIXTURE_DIR}
SITE_DIR="$FIXTURE_DIR/nginx"
ZIP="$FIXTURE_DIR/nginx.zip"
PORT=${DERRIDAI_SITE_PORT:-18080}
IMAGE=${DERRIDAI_SITE_IMAGE:-derridai-publication-acceptance}
CONTAINER=${DERRIDAI_SITE_CONTAINER:-derridai-publication-acceptance}

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker image rm -f "$IMAGE" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

rm -rf "$SITE_DIR"
mkdir -p "$SITE_DIR"
unzip -q "$ZIP" -d "$SITE_DIR"

test -x "$SITE_DIR/start.sh"
test -x "$SITE_DIR/stop.sh"

(
  cd "$SITE_DIR"
  DERRIDAI_SITE_PORT="$PORT" \
  DERRIDAI_SITE_IMAGE="$IMAGE" \
  DERRIDAI_SITE_CONTAINER="$CONTAINER" \
    ./start.sh
)

test "$(curl -fsS "http://127.0.0.1:$PORT/healthz")" = "ok"
curl -fsS "http://127.0.0.1:$PORT/" | grep -Fq "DerridAI publication acceptance"
test "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/provider")" = "308"
docker container inspect "$CONTAINER" >/dev/null

(
  cd "$SITE_DIR"
  DERRIDAI_SITE_CONTAINER="$CONTAINER" ./stop.sh
)

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Publication acceptance container still exists after stop.sh" >&2
  exit 1
fi
