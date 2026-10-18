#!/usr/bin/env python3
"""Ponto de entrada simples para executar o ReaDroid no Termux.

Termux já é UTF-8, mas um LANG/LC_ALL herdado de outro lugar (ou uma sessão
ssh) pode deixar o stdout num codepage de 1 byte. Aí um "ç" na saída derruba
o menu com UnicodeEncodeError. reconfiguramos antes de qualquer print.
"""
from __future__ import annotations

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

from readroid.app import main

if __name__ == "__main__":
    main()