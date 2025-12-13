#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q .

if command -v ruff >/dev/null 2>&1; then
  ruff check .
else
  echo "ruff not installed (optional): pip install ruff"
fi
