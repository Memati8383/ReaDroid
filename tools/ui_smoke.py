"""Renderiza as telas principais sem APK, para conferir a traducao na mao.

    python tools/ui_smoke.py            # usa o idioma detectado
    READROID_LANG=pt python tools/ui_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import i18n
from readroid.app import (banner, browse_generated_files, dependencies, keystore_menu,
                          print_menu, quick_edits_menu, rebuild_and_sign)
from readroid.builder import QUICK_EDIT_KEYS

i18n.reload_for_tests(None)

print(f"### idioma ativo: {i18n.active_lang()}")
banner()
print_menu()
print()
dependencies()
print()
print(i18n.t("quick.title"))
for i, key in enumerate(QUICK_EDIT_KEYS, 1):
    print(f" [{i}] {i18n.t('builder.edit.' + key)}")
print()
print(i18n.t("build.title"))
print(i18n.t("build.warn1"))
print(i18n.t("build.warn2"))
print()
print(i18n.t("keys.title"))
print(i18n.t("keys.none_yet"))
print()
print(i18n.t("gen.title"))
print(i18n.t("gen.output"))
print(i18n.t("gen.reports"))
print(i18n.t("gen.builds"))
print(i18n.t("gen.back"))
print()
print(i18n.t("report.strings_summary", urls=12, domains=40, ips=3))
print(i18n.t("report.zip_summary", files=120, dex=2, libs=1))
print(i18n.t("analyzer.jadx.partial", code=1, files=42, java=30))
print(i18n.t("builder.rename.done", old="com.velho.app", new="com.novo.pacote"))
print(i18n.t("analyzer.warn.extension", ext=i18n.t("analyzer.no_extension")))