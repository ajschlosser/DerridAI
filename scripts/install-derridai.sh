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

REPOSITORY="ajschlosser/DerridAI"
VERSION=""
INSTALL_DIR=""

usage() {
  cat <<'EOF'
Install the DerridAI native CLI.

Usage:
  install-derridai.sh [--version VERSION] [--install-dir DIR]

Without --version, installs the latest GitHub release.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || { echo "Missing value for --version" >&2; exit 2; }
      VERSION="$2"
      shift 2
      ;;
    --install-dir)
      [ "$#" -ge 2 ] || { echo "Missing value for --install-dir" >&2; exit 2; }
      INSTALL_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

system=$(uname -s)
machine=$(uname -m)

case "$system:$machine" in
  Linux:x86_64|Linux:amd64)
    target="linux-x86_64"
    ;;
  Darwin:arm64|Darwin:aarch64)
    target="macos-arm64"
    ;;
  Darwin:x86_64|Darwin:amd64)
    target="macos-x86_64"
    ;;
  *)
    echo "Unsupported DerridAI binary target: $system $machine" >&2
    exit 3
    ;;
esac

asset="derridai-$target"
checksum_asset="$asset.sha256"

if [ -n "$VERSION" ]; then
  case "$VERSION" in
    v*) tag="$VERSION" ;;
    *) tag="v$VERSION" ;;
  esac
  base_url="https://github.com/$REPOSITORY/releases/download/$tag"
else
  base_url="https://github.com/$REPOSITORY/releases/latest/download"
fi

if [ -z "$INSTALL_DIR" ]; then
  if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
  else
    INSTALL_DIR="$HOME/.local/bin"
  fi
fi

if command -v curl >/dev/null 2>&1; then
  download() {
    curl -fL --retry 3 --retry-delay 1 -o "$2" "$1"
  }
elif command -v wget >/dev/null 2>&1; then
  download() {
    wget -q --tries=3 -O "$2" "$1"
  }
else
  echo "curl or wget is required to install DerridAI." >&2
  exit 4
fi

tmpdir=$(mktemp -d 2>/dev/null || mktemp -d -t derridai)
trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM

binary_path="$tmpdir/$asset"
checksum_path="$tmpdir/$checksum_asset"

echo "Downloading DerridAI for $target..." >&2
download "$base_url/$asset" "$binary_path"
download "$base_url/$checksum_asset" "$checksum_path"

expected=$(awk 'NR == 1 { print $1 }' "$checksum_path")
[ -n "$expected" ] || { echo "Downloaded checksum file is empty." >&2; exit 5; }

if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$binary_path" | awk '{ print $1 }')
elif command -v shasum >/dev/null 2>&1; then
  actual=$(shasum -a 256 "$binary_path" | awk '{ print $1 }')
else
  echo "sha256sum or shasum is required to verify DerridAI." >&2
  exit 4
fi

if [ "$actual" != "$expected" ]; then
  echo "Checksum verification failed; refusing to install DerridAI." >&2
  exit 5
fi

mkdir -p "$INSTALL_DIR"
destination="$INSTALL_DIR/derridai"
cp "$binary_path" "$destination"
chmod 755 "$destination"

echo "Installed $destination" >&2
"$destination" --version

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    echo "Add $INSTALL_DIR to PATH to run 'derridai' from any shell." >&2
    ;;
esac
