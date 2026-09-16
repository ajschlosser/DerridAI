#!/usr/bin/env sh
# Copyright 2026 Aaron John Schlosser, PhD.
set -eu

DATA_DIR="${1:-./data}"
UID_VALUE="$(id -u)"
GID_VALUE="$(id -g)"

echo "Repairing DerridAI data ownership for UID ${UID_VALUE}, GID ${GID_VALUE}: ${DATA_DIR}"
sudo chown -R "${UID_VALUE}:${GID_VALUE}" "${DATA_DIR}"
chmod -R u+rwX "${DATA_DIR}"
echo "Done."
