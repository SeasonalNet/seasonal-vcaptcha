#!/usr/bin/env python3
"""Legacy compatibility wrapper for the old vosk_digits.py entrypoint."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from seasonal_vcaptcha.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
