#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

./.venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.port 8501
