#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${APP_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "Run ./install.sh first." >&2
  exit 1
fi
exec "${PYTHON}" "${APP_DIR}/scripts/start.py" "$@"
