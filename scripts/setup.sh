#!/usr/bin/env bash
# Create .venv and install requirements. Run from repo root:
#   chmod +x scripts/setup.sh && ./scripts/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f corpus/url_manifest.yaml ]]; then
  echo "Run from project root (corpus/url_manifest.yaml missing)." >&2
  exit 1
fi
PY="${PYTHON:-python3}"
if ! command -v "$PY" &>/dev/null; then
  PY="python"
fi
if ! "$PY" -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
  echo "Need Python 3.10+ on PATH (got: $PY)." >&2
  exit 1
fi
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "Done. Use: source .venv/bin/activate   then   python scripts/validate_manifest.py"
