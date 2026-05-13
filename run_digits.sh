#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
export VOSK_MODEL="$BASE/model-small-en-us"
. "$BASE/venv/bin/activate"
python3 "$BASE/vosk_digits.py" "$1"
