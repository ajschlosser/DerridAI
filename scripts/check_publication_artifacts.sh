#!/bin/sh
# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
