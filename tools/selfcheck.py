"""Auto-teste do ReaDroid: roda depois do instalador e diz se está utilizável.

    python tools/selfcheck.py

Não precisa de APK nem de rede. Cobre o que quebra em campo: import quebrado,
catálogo pela metade, banner que estoura a borda, idioma que não resolve,
Python velho demais.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

MIN_PYTHON = (3, 9)
REQUIRED_TOOLS = ["git"]
OPTIONAL_TOOLS = ["java", "jadx", "apktool", "aapt", "aapt2", "zipalign",
                  "apksigner", "jarsigner", "keytool", "less", "termux-open"]

problems: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "OK  " if ok else "FALHA"
    print(f"[{mark}] {label}" + (f" - {detail}" if detail else ""))
    if not ok:
        problems.append(label)
    return ok


def main() -> int:
    print("ReaDroid - autoteste\n")

    version = sys.version_info[:2]
    check(f"Python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
          version >= MIN_PYTHON, f"encontrado {version[0]}.{version[1]}")

    check("executando a partir do checkout", (ROOT / "readroid" / "app.py").is_file(), str(ROOT))

    # --- import e catálogo -------------------------------------------------
    try:
        from readroid import __version__, i18n
        from readroid.app import MENU, banner, print_menu
        from readroid.analyzer import inspect_apk, scan_strings
        from readroid.builder import QUICK_EDIT_KEYS
        check("import dos módulos", True, f"v{__version__}")
    except Exception as exc:  # noqa: BLE001 - o relatório precisa do traceback
        check("import dos módulos", False, repr(exc))
        print("\nO código não importa; o resto do autoteste não faz sentido.")
        return 1

    for lang in ("tr", "pt"):
        i18n.reload_for_tests(lang)
        table = i18n.table()
        holes = [k for k in table if not table[k].strip()]
        check(f"catálogo {lang} carregado", bool(table) and not holes,
              f"{len(table)} chaves")

    # Toda chave usada no código precisa existir nos dois catálogos.
    pattern = re.compile(r"""t\(\s*f?["']([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)["']""")
    used = set()
    for path in (ROOT / "readroid").glob("*.py"):
        used.update(pattern.findall(path.read_text(encoding="utf-8")))
    for key in QUICK_EDIT_KEYS:
        used.add(f"builder.edit.{key}")
    i18n.reload_for_tests("tr")
    missing = sorted(k for k in used if k not in i18n.table())
    check("toda chave usada no código existe", not missing,
          f"{len(used)} chaves" if not missing else ", ".join(missing[:5]))

    # --- interface em várias larguras de terminal ----------------------------
    # As linhas saem com códigos ANSI; eles ocupam zero colunas na tela, então
    # precisam sair da conta antes de medir a largura.
    ansi = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    for cols in (32, 40, 50, 72):
        os.environ["COLUMNS"] = str(cols)
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                banner()
                print_menu()
            lines = [ansi.sub("", ln) for ln in buffer.getvalue().splitlines()]
            overflow = [ln for ln in lines[:4] if len(ln) > cols]
            check(f"banner cabe em {cols} colunas", not overflow,
                  f"caixa de {len(lines[0])} colunas" if not overflow
                  else f"linha de {len(overflow[0])} caracteres: {overflow[0][:cols]}")
        except Exception as exc:  # noqa: BLE001
            check(f"banner cabe em {cols} colunas", False, repr(exc))
    os.environ.pop("COLUMNS", None)

    # --- fluxo real com um APK mínimo --------------------------------------
    manifest = (b'<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
                b'package="com.teste.app" android:versionName="1.0">'
                b'<uses-permission android:name="android.permission.INTERNET"/>'
                b'<application android:label="Teste"><activity android:name=".A"/></application>'
                b'</manifest>')
    with tempfile.TemporaryDirectory() as tmp:
        apk = Path(tmp) / "teste.apk"
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("AndroidManifest.xml", manifest)
            archive.writestr("classes.dex", b"dex\n035\x00 https://teste.example.org 10.0.0.1")
        try:
            report = inspect_apk(apk)
            check("inspeção de APK", report["zip_entry_count"] == 2,
                  f"sha256 {report['sha256'][:12]}...")
            scan = scan_strings(apk)
            check("scanner de strings", "teste.example.org" in scan["domains"],
                  f"{len(scan['urls'])} URL, {len(scan['domains'])} alan adı")
            with tempfile.TemporaryDirectory() as out:
                target = Path(out) / "r.json"
                from readroid.analyzer import write_report
                write_report(report, target)
                json.loads(target.read_text(encoding="utf-8"))
            check("escrita de relatório JSON", True)
        except Exception as exc:  # noqa: BLE001
            check("análise de APK", False, repr(exc))

    # --- ferramentas externas ------------------------------------------------
    print("\nFerramentas externas:")
    for name in REQUIRED_TOOLS:
        path = shutil.which(name)
        check(f"obrigatória: {name}", bool(path), path or "não encontrada")
    for name in OPTIONAL_TOOLS:
        path = shutil.which(name)
        state = path or "ausente (opcional)"
        print(f"[INFO] {name}: {state}")

    try:
        result = subprocess.run(["pkg", "--version"], capture_output=True, text=True, timeout=10)
        check("ambiente Termux", result.returncode == 0, "pkg disponível")
    except (OSError, subprocess.TimeoutExpired):
        notes.append("fora do Termux (sem pkg) - verificação das dependências foi parcial")

    # --- escreve e lê um relatório de verdade -------------------------------
    if notes:
        print("\nObservações:")
        for note in notes:
            print(" -", note)

    print()
    if problems:
        print(f"FALHOU ({len(problems)}): " + ", ".join(problems))
        return 1
    print("Tudo certo. Rode: python readroid.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())