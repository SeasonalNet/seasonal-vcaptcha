#!/usr/bin/env bash
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
  printf '\n'
  exit 2
fi

# Legacy-compatible default. Operators may override VOSK_MODEL when the model is
# installed somewhere else.
export VOSK_MODEL="${VOSK_MODEL:-$BASE/model-small-en-us}"
export PYTHONPATH="$BASE/lib${PYTHONPATH:+:$PYTHONPATH}"

if [[ -f "$BASE/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  . "$BASE/venv/bin/activate"
fi

exec python3 -m seasonal_vcaptcha.cli "$@"
