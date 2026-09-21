#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PYTHON_BIN=""
for candidate in python3.12 python3.13 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    PYTHON_BIN="$candidate"
    break
  fi
done
if [[ -z "$PYTHON_BIN" ]]; then
  echo 'Python 3.11+ is required. See README.md for Ubuntu 22.04 and the uv alternative.' >&2
  exit 2
fi
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install 'kaggle==2.2.4' 'kagglesdk==0.1.37'
echo 'Setup complete. Next: .venv/bin/kaggle auth login --no-launch-browser'
