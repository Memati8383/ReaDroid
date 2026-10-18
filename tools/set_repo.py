"""Preenche o placeholder de repositório em todo o projeto de uma vez.

    python tools/set_repo.py https://github.com/SEU_USUARIO/ReaDroid-TR.git
    python tools/set_repo.py --check

Saiu do --check: lista os arquivos que ainda têm placeholder, para você não
publicar um README com "<KULLANICI-ADIN>" no meio.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Só estes: <KULLANICI-ADIN> é o usuário, <app> e <lang> são exemplos de
# documentação que fazem sentido continuarem como estão.
PLACEHOLDER_RE = re.compile(r"<KULLANICI-ADIN>|github\.com/SEU_USUARIO")
TARGETS = ["install.sh", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"]

SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def normalize(url: str) -> str:
    url = url.strip().rstrip("/")
    if not SLUG_RE.match(url):
        raise SystemExit(f"URL invalida: {url!r} (esperado usuario/repositorio)")
    if url.endswith(".git"):
        url = url[:-4]
    return url


def main() -> int:
    ap = argparse.ArgumentParser(description="preenche o placeholder de repositorio")
    ap.add_argument("url", nargs="?", help="https://github.com/USUARIO/ReaDroid-TR")
    ap.add_argument("--check", action="store_true", help="apenas relata, nao escreve")
    args = ap.parse_args()

    if args.check or not args.url:
        # Em --check o silêncio é sucesso: a saída serve para o CI, que só precisa
        # do código de saída. Os achados vão para stderr para não poluir stdout.
        found = False
        for name in TARGETS:
            path = ROOT / name
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if PLACEHOLDER_RE.search(line):
                    found = True
                    print(f"{name}:{number}: {line.strip()[:100]}", file=sys.stderr)
        if found:
            print("\nrode: python tools/set_repo.py https://github.com/USUARIO/ReaDroid-TR",
                  file=sys.stderr)
            return 1
        return 0

    url = normalize(args.url)
    raw_base = f"https://raw.githubusercontent.com/{url}"
    clone = f"https://github.com/{url}.git"

    changed = []
    for name in TARGETS:
        path = ROOT / name
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        updated = original.replace("https://github.com/<KULLANICI-ADIN>/ReaDroid-TR.git", clone)
        updated = updated.replace("https://github.com/SEU_USUARIO/ReaDroid-TR.git", clone)
        updated = updated.replace("<KULLANICI-ADIN>", url.split("/")[0])
        updated = re.sub(r"https://raw\.githubusercontent\.com/[A-Za-z0-9_.-]+/ReaDroid-TR/main",
                         f"{raw_base}/main", updated)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(name)

    if not changed:
        print("nada mudou (ja estava preenchido?)")
        return 0
    print(f"atualizado: {', '.join(changed)}")
    print(f"clone  : {clone}")
    print(f"curl   : bash -c \"$(curl -fsSL {raw_base}/main/install.sh)\"")
    print(f"remote : git remote add origin {clone}")
    return 0


if __name__ == "__main__":
    sys.exit(main())