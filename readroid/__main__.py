"""Permite "python -m readroid" com a mesma garantia de UTF-8 do readroid.py."""
from __future__ import annotations

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

from .app import main

if __name__ == "__main__":
    main()