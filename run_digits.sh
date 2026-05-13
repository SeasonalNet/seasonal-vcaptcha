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

args=("$@")
has_config=0
for arg in "${args[@]}"; do
  case "$arg" in
    --config|--config=*)
      has_config=1
      ;;
  esac
done

if [[ "$has_config" -eq 0 && -f /etc/seasonal-vcaptcha/config.yaml ]]; then
  args=(--config /etc/seasonal-vcaptcha/config.yaml "${args[@]}")
fi

exec python3 -m seasonal_vcaptcha.cli "${args[@]}"
