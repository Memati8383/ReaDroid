"""Rapor üretimini uçtan uca dener: sahte APK'yı analiz eder, JSON raporu
yazar ve çevirinin gerçekten dosyaya düştüğünü doğrular.

    python tools/e2e_check.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from readroid import i18n
from readroid.analyzer import analyze_manifest, inspect_apk, scan_strings
from readroid.app import save_and_show

MANIFEST = (
    b'<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.ornek.uygulama" '
    b'android:versionCode="3" android:versionName="1.2.3">'
    b'<uses-permission android:name="android.permission.INTERNET"/>'
    b'<uses-permission android:name="android.permission.READ_SMS"/>'
    b'<application android:label="Ornek" android:debuggable="false">'
    b'<activity android:name=".Ana" android:exported="true"/>'
    b'</application></manifest>'
)

DEX = (b"dex\n035\x00 https://ornek.example.com/api test.ornek.org 192.168.1.2 "
       b"android.content.pm.PackageManager alt.example.com")


def make_apk(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("AndroidManifest.xml", MANIFEST)
        z.writestr("classes.dex", DEX)
        z.writestr("res/values/strings.xml", b"<resources/>")
        z.writestr("AndroidManifest.xml.bin", b"")
    return path


def main() -> int:
    i18n.reload_for_tests(None)
    print(f"idioma: {i18n.active_lang()}")
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        apk = make_apk(tmp_path / "ornek.bin")  # bilinen olmayan uzantı -> uyarı bekleniyor

        report = inspect_apk(apk)
        save_and_show(report, "inspection", apk)
        if not report["warnings"]:
            failures.append("bilinmeyen uzantı için uyarı üretilmedi")
        if report["manifest"]["format"] != i18n.t("analyzer.manifest.text_xml"):
            failures.append(f"manifest formatı çevrilmedi: {report['manifest']['format']}")

        manifest_report = analyze_manifest(apk, tmp_path / "work")
        if len(manifest_report["permissions"]) != 2:
            failures.append(f"izin sayısı beklenenden farklı: {len(manifest_report['permissions'])}")
        if manifest_report.get("decoded") is not True:
            failures.append("manifest cozulemedi")

        scan = scan_strings(apk)
        if "android.content.pm.packagemanager" in scan["domains"]:
            failures.append("sinif adi alan adi sanildi")
        if "test.ornek.org" not in scan["domains"]:
            failures.append(f"gercek alan adi bulunamadi: {scan['domains']}")

        written = sorted((ROOT / "reports").glob("ornek_inspection_*.json"))
        if not written:
            failures.append("rapor dosyasi yazilmadi")
        else:
            data = json.loads(written[-1].read_text(encoding="utf-8"))
            if data["note"] != i18n.t("analyzer.note.inspect"):
                failures.append("rapordaki 'note' cevrilmemis")
            print(f"rapor: {written[-1].name}")
            print(f"  note  : {data['note']}")
            print(f"  format: {data['manifest']['format']}")
            print(f"  warn  : {data['warnings']}")

    if failures:
        print("\nBASARISIZ:")
        for item in failures:
            print(" -", item)
        return 1
    print("\nTAMAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())