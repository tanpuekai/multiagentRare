#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

./.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8501 --reload
