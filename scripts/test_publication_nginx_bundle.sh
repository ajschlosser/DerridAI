#!/bin/sh
set -eu

BUNDLE_DIR=${1:?usage: test_publication_nginx_bundle.sh <extracted-bundle-dir>}
PORT=${DERRIDAI_SITE_PORT:-18080}
IMAGE=${DERRIDAI_SITE_IMAGE:-derridai-publication-acceptance}
CONTAINER=${DERRIDAI_SITE_CONTAINER:-derridai-publication-acceptance}

export DERRIDAI_SITE_PORT="$PORT"
export DERRIDAI_SITE_IMAGE="$IMAGE"
export DERRIDAI_SITE_CONTAINER="$CONTAINER"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker image rm -f "$IMAGE" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

cd "$BUNDLE_DIR"
./start.sh

health=$(curl --fail --silent --show-error "http://127.0.0.1:${PORT}/healthz")
[ "$health" = "ok" ]

index=$(curl --fail --silent --show-error "http://127.0.0.1:${PORT}/")
printf '%s' "$index" | grep -F "DerridAI Publication Acceptance" >/dev/null
printf '%s' "$index" | grep -F 'src="./derridai-site.js"' >/dev/null

runtime=$(curl --fail --silent --show-error "http://127.0.0.1:${PORT}/derridai-site.js")
printf '%s' "$runtime" | grep -F "globalThis.__DERRIDAI_SITE_PACKAGE__=" >/dev/null
printf '%s' "$runtime" | grep -F "createClient" >/dev/null

./stop.sh
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Publication container still exists after stop.sh." >&2
  exit 1
fi

docker image rm -f "$IMAGE" >/dev/null 2>&1 || true
trap - EXIT INT TERM
