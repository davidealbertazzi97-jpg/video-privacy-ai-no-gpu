#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${APP_DIR}/bin"

if cc -O2 -Wall -Wextra -fPIC -shared \
  "${APP_DIR}/native/netguard.c" \
  -o "${APP_DIR}/bin/liblocal_ai_netguard.so" 2>/dev/null; then
  chmod 0755 "${APP_DIR}/bin/liblocal_ai_netguard.so"
  echo "Linux native network guard installed."
else
  echo "Optional Linux native network guard build skipped."
fi

