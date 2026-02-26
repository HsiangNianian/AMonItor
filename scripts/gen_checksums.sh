#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
if [ ! -d dist ]; then
  echo "dist not found"
  exit 1
fi

cd dist
sha256sum amonitor-agent-* > SHA256SUMS

echo "checksums generated: dist/SHA256SUMS"
