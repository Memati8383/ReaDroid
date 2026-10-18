#!/usr/bin/env python3
"""Inventário de strings traduzíveis do ReaDroid.

Varre os módulos Python e o install.sh, lista cada literal de string com
arquivo:linha, separa o que é texto de interface do que é identificador,
caminho ou nome de ferramenta, e gera um esqueleto de locales/tr.keys.json
para a tradução.

Uso:
    python tools/extract_strings.py            # escreve o inventário + esqueleto
    python tools/extract_strings.py --check    # só relatório no stdout, não escreve
    python tools/extract_strings.py --stats    # contagem por arquivo

Docstrings e comentários NÃO entram: são código, não interface, e o upstream
pede comentários em português (ver CONTRIBUTING.md).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "locales" / "worklist.json"
OUT_SKELETON = ROOT / "locales" / "tr.keys.json"

PY_MODULES = ["readroid/app.py", "readroid/analyzer.py", "readroid/builder.py",
              "readroid/axml.py", "readroid/__init__.py", "readroid/__main__.py"]
SHELL_FILES = ["install.sh"]

# Nomes de ferramenta e termos técnicos que ficam em inglês/latin em qualquer
# idioma - traduzir "apktool" Breakaria a leitura do comando.
TECHNICAL = {
    "apktool", "jadx", "apksigner", "zipalign", "jarsigner", "keytool", "aapt",
    "aapt2", "java", "python", "unzip", "git", "pkg", "less", "termux-open",
    "openjdk-21", "termux-setup-storage", "readroid.py", "apktool.yml",
    "AndroidManifest.xml", "apktool.json", "classes.dex", "readroid",
    "builds", "reports", "output", "smali", "APK", "APKs", "SHA256", "JSON",
    "AXML", "TLD", "MIT", "Termux", "Android", "Google", "HTTP", "INTERNET",
    "debuggable", "allowBackup", "usesCleartextTraffic", "applicationId",
    "reflection", "DRM", "Open Source Project", "dex", "resources",
    "metadados", "ReaDroid", "OffensiveTec", "UTF-8",
}

# Padrões que denunciam literal não-humano: cor ANSI, regex, caminho, format,
# nome de arquivo interno, chave de dicionário de machine output.
NOT_TEXT = [
    re.compile(r"^\x1b\["),
    re.compile(r"^%[-+ #0-9.]*[a-zA-Z]$"),
    re.compile(r"^[a-z_]+$"),                      # identificador / chave snake_case
    re.compile(r"^\d+$"),
    re.compile(r"^[/\\.]{1,2}[/\\]?|^~"),          # caminho
    re.compile(r"^[a-zA-Z]:\\"),                   # caminho Windows
    re.compile(r"^[\w.\-/]+\.(py|yml|yaml|json|xml|jks|apk|txt|sh)$", re.I),
    re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\("),      # chamada
    re.compile(r"[\[\]{}()<>*+?|^$]{2,}"),          # regex
]

# Chaves de relatório JSON que um humano consome: traduzimos o valor, nunca a chave.
JSON_KEYS = {
    "tool", "version", "analyzed_at_utc", "file_name", "file_size_bytes", "sha256",
    "zip_entry_count", "dex_files", "native_libraries", "resource_file_count",
    "asset_file_count", "file_list_sample", "note", "warnings", "permissions",
    "components", "application", "package", "version_code", "version_name",
    "decoded", "decoded_by", "urls", "domains", "ipv4_candidates", "bytes_scanned",
    "large_entries_skipped", "truncated_categories", "optional_tool_runs", "ok",
    "message", "warning", "final_apk", "steps", "skipped", "stderr", "stdout",
    "returncode", "applied", "manifest", "old_package", "new_package",
    "directories_moved", "files_updated", "output_dir", "files_generated",
    "scheme", "created", "path", "alias", "v1 + v2 + v3", "readroid (leitor AXML nativo)",
}


def classify(text: str) -> str:
    """Devolve 'ui', 'technical' ou 'skip' para um literal."""
    if not text.strip():
        return "skip"
    if text in TECHNICAL or text in JSON_KEYS:
        return "technical"
    if any(p.search(text) for p in NOT_TEXT):
        return "skip"
    letters = re.findall(r"[A-Za-zÀ-ÿ]{2,}", text)
    if not letters:
        return "skip"
    if len(text.strip()) < 3:
        return "skip"
    # Texto de interface tem espaço OU é uma palavra de menu curta ("Sair").
    if " " not in text and len(text.strip()) > 24:
        return "skip"
    return "ui"


def slug(text: str, module: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40].strip("_")
    if not base:
        base = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{module}.{base}"


def py_inventory(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    module = path.stem
    # docstrings de módulo/classe/função não são interface
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

    found: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        seg = ast.get_source_segment(src, node)
        entry = {"file": str(path.relative_to(ROOT)).replace("\\", "/"),
                 "line": node.lineno, "text": node.value}
        if seg and ("f\"" in seg or "f'" in seg or seg.startswith(("f\"", "f'"))):
            # f-string: guarda também o segmento cru (chaves de interpolação importam)
            entry["raw"] = seg
        found.append(entry)
    return found


SHELL_STRING = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'')


def shell_inventory(path: Path) -> list[dict]:
    found = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for m in SHELL_STRING.finditer(line):
            text = m.group(1) or m.group(2) or ""
            if not text.strip():
                continue
            found.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"),
                          "line": n, "text": text, "raw": line.strip()})
    return found


def build() -> tuple[dict, dict]:
    entries: list[dict] = []
    for rel in PY_MODULES:
        p = ROOT / rel
        if p.is_file():
            entries.extend(py_inventory(p))
    for rel in SHELL_FILES:
        p = ROOT / rel
        if p.is_file():
            entries.extend(shell_inventory(p))

    ui: dict[str, dict] = {}
    technical: dict[str, list] = {}
    for e in entries:
        kind = classify(e["text"])
        if kind == "skip":
            continue
        site = f'{e["file"]}:{e["line"]}'
        if kind == "technical":
            technical.setdefault(e["text"], []).append(site)
            continue
        key = slug(e["text"], e["file"].replace("readroid/", "").replace(".py", "").replace("/", "."))
        # colisão de slug (textos diferentes com o mesmo esqueleto) -> sufixo estável
        while key in ui and ui[key]["pt"] != e["text"]:
            key += "_2"
        ui.setdefault(key, {"pt": e["text"], "tr": "", "sites": []})
        if site not in ui[key]["sites"]:
            ui[key]["sites"].append(site)

    return ui, technical


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="não escreve arquivos")
    ap.add_argument("--stats", action="store_true", help="só contagens")
    args = ap.parse_args()

    ui, technical = build()

    by_file: dict[str, int] = {}
    for item in ui.values():
        for site in item["sites"]:
            f = site.rsplit(":", 1)[0]
            by_file[f] = by_file.get(f, 0) + 1

    print("== strings de interface por arquivo ==")
    for f, n in sorted(by_file.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {f}")
    print(f"  {sum(by_file.values()):4d}  TOTAL (ocorrências)")
    print(f"  {len(ui):4d}  TOTAL (literais únicos)")
    print(f"  {len(technical):4d}  literais técnicos mantidos como estão")

    if args.stats:
        return 0

    if not args.check:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding="utf-8")
        OUT_SKELETON.write_text(json.dumps(
            {k: v["pt"] for k, v in ui.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nescrito: {OUT_JSON.relative_to(ROOT)}")
        print(f"escrito: {OUT_SKELETON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())