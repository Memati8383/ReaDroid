"""Interface de terminal do ReaDroid. Mantemos o menu simples para telas pequenas."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import __version__
from .analyzer import (analyze_manifest, decompile_with_jadx, extension_warning, extract_smali_with_apktool,
                       inspect_apk, scan_strings, write_report)
from .builder import (DEFAULT_ALIAS, DEFAULT_STOREPASS, QUICK_EDIT_KEYS, apply_quick_edits, build_pipeline,
                      rename_package, valid_package_name, verify_apk)
from .i18n import is_exit, is_other_path, is_yes, t

# Usa a pasta desta cópia do projeto, não uma pasta fixa em ~/ReaDroid.
# Isso evita salvar os resultados em outro lugar quando o projeto foi extraído
# em Downloads ou executado a partir de um clone do GitHub.
BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"
OUTPUTS = BASE / "output"
BUILDS = BASE / "builds"
KEYSTORE = BASE / ".readroid-keystore.jks"
GREEN, CYAN, YELLOW, RED, DIM, RESET, BOLD = "\033[92m", "\033[96m", "\033[93m", "\033[91m", "\033[2m", "\033[0m", "\033[1m"

# Remove sequências de escape ANSI e caracteres de controle antes de imprimir qualquer
# dado que veio de dentro de um APK (strings, nomes de arquivo, saída de ferramentas).
# Sem isso, um APK malicioso poderia manipular as cores/o cursor do seu terminal.
_CTRL_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str) -> str:
    return _CTRL_RE.sub("", str(text))


def clear() -> None:
    os.system("clear" if os.environ.get("TERM") else "")


def width() -> int:
    return max(32, min(shutil.get_terminal_size((44, 24)).columns, 78))


def banner() -> None:
    clear()
    title = f" ReaDroid v{__version__}"
    subtitle = t("banner.subtitle")
    # A caixa nasce do conteúdo, não de um número fixo: o texto traduzido pode ser
    # mais largo que o original e estourar a borda num terminal estreito.
    inner = min(max(len(title), len(subtitle)) + 2, width() - 2)
    print(GREEN + "╭" + "─" * inner + "╮" + RESET)
    print(GREEN + "│" + RESET + BOLD + title.ljust(inner) + RESET + GREEN + "│" + RESET)
    print(GREEN + "│" + RESET + CYAN + subtitle.ljust(inner) + RESET + GREEN + "│" + RESET)
    print(GREEN + "╰" + "─" * inner + "╯" + RESET)
    print((" " * max(inner - 12, 0)) + DIM + t("banner.watermark") + RESET)


def safe_input(prompt: str = "") -> str:
    """input() que não derruba o menu com traceback se o terminal fechar (Ctrl+D/Ctrl+C)."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def pause() -> None:
    safe_input("\n" + t("ui.pause"))


def ask_apk() -> Path | None:
    # Para deixar o fluxo mais rápido no celular, tentamos encontrar APKs nas pastas comuns.
    candidates: list[Path] = []
    search_dirs = [Path.cwd(), Path.home() / "storage" / "downloads",
                   Path.home() / "storage" / "shared" / "Download",
                   Path.home() / "storage" / "shared" / "Documents",
                   Path("/storage/emulated/0/Download")]
    seen: set[str] = set()
    for folder in search_dirs:
        if not folder.is_dir():
            continue
        try:
            for item in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if (item.is_file() and item.suffix.lower() in (".apk", ".apks", ".xapk")
                        and str(item) not in seen):
                    candidates.append(item)
                    seen.add(str(item))
        except OSError:
            # Uma pasta sem permissão não deve impedir o uso das demais.
            continue
    candidates = candidates[:20]
    if candidates:
        print(CYAN + t("apk.found") + RESET)
        for index, item in enumerate(candidates, 1):
            try:
                size_mb = item.stat().st_size / (1024 * 1024)
                print(f" [{index}] {sanitize(item.name)} ({size_mb:.1f} MB)")
            except OSError:
                print(f" [{index}] {sanitize(item.name)}")
        print(t("apk.other"))
        choice = safe_input(t("apk.choose")).strip()
        if not is_other_path(choice):
            try:
                return candidates[int(choice) - 1]
            except (ValueError, IndexError):
                print(YELLOW + t("apk.bad_choice") + RESET)
    raw = safe_input(t("apk.path")).strip().strip('"').strip("'")
    if not raw:
        print(YELLOW + t("apk.empty_path") + RESET)
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists() or not path.is_file():
        print(RED + t("apk.not_found") + RESET)
        return None
    warning = extension_warning(path)
    if warning:
        print(YELLOW + warning + RESET)
    return path


def ask_decoded_dir() -> Path | None:
    """Lista pastas já decodificadas pelo Apktool (opção 5) e deixa escolher ou digitar outra."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    candidates = sorted((p for p in OUTPUTS.glob("*_apktool") if p.is_dir()),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:15]
    if candidates:
        print(CYAN + t("dir.decoded_found") + RESET)
        for index, item in enumerate(candidates, 1):
            print(f" [{index}] {sanitize(item.name)}")
        print(t("apk.other"))
        choice = safe_input(t("dir.choose")).strip()
        if not is_other_path(choice):
            try:
                return candidates[int(choice) - 1]
            except (ValueError, IndexError):
                print(YELLOW + t("apk.bad_choice") + RESET)
    raw = safe_input(t("dir.path")).strip().strip('"').strip("'")
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        print(RED + t("dir.not_found") + RESET)
        return None
    return path


def save_and_show(report: dict, prefix: str, apk: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = REPORTS / f"{apk.stem}_{prefix}_{stamp}.json"
    write_report(report, target)
    print(GREEN + "\n" + t("report.saved", target=target) + RESET)


def run_action(key: str, action: Callable[[Path], dict]) -> None:
    # "key" é um identificador estável em ASCII: o nome do arquivo de relatório
    # não deve depender do idioma da interface.
    print(CYAN + "\n" + t(f"action.{key}.title") + RESET)
    apk = ask_apk()
    if apk is None:
        return
    try:
        report = action(apk)
        save_and_show(report, key, apk)
        for warning in report.get("warnings", []):
            print(YELLOW + warning + RESET)
        if "permissions" in report:
            print(t("report.permissions_found", count=len(report.get('permissions', []))))
            for item in report.get("permissions", [])[:25]:
                print(" •", sanitize(item.get("name", "")))
            if not report.get("decoded"):
                print(YELLOW + t("report.manifest_not_decoded") + RESET)
        if "urls" in report:
            print(t("report.strings_summary", urls=len(report['urls']),
                    domains=len(report['domains']), ips=len(report['ipv4_candidates'])))
            if report.get("truncated_categories"):
                print(YELLOW + t("report.truncated",
                                 names=', '.join(report['truncated_categories'])) + RESET)
        if "zip_entry_count" in report:
            print(t("report.zip_summary", files=report['zip_entry_count'],
                    dex=len(report['dex_files']), libs=len(report['native_libraries'])))
    except Exception as exc:  # O menu não deve fechar por um erro inesperado de um arquivo.
        print(RED + t("report.failed", error=exc) + RESET)
        print(t("report.original_untouched"))


def dependencies() -> None:
    print(CYAN + "\n" + t("deps.title") + RESET)
    for name in ("python", "java", "jadx", "apktool", "aapt", "aapt2", "zipalign", "apksigner", "keytool", "unzip", "git"):
        path = shutil.which(name)
        print(f"[{GREEN + 'OK' + RESET if path else YELLOW + '--' + RESET}] {name}: {path or t('deps.not_found')}")
    if shutil.which("java"):
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
            print(sanitize((result.stderr or result.stdout).splitlines()[0]))
        except (OSError, subprocess.TimeoutExpired, IndexError):
            print(t("deps.java_no_version"))
    if shutil.which("jadx"):
        try:
            result = subprocess.run(["jadx", "--version"], capture_output=True, text=True, timeout=8)
            print("JADX:", sanitize((result.stdout or result.stderr).strip().splitlines()[0]))
        except (OSError, subprocess.TimeoutExpired, IndexError):
            print(t("deps.jadx_no_version"))
    print(CYAN + "\n" + t("deps.build_hint") + RESET)


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    print(t("folder.path", path=path))
    print(t("folder.content"))
    items = list(path.iterdir())
    if not items:
        print(t("folder.empty"))
    for item in sorted(items, key=lambda p: p.name.lower())[:60]:
        print(" [DIR]" if item.is_dir() else " [FILE]", sanitize(item.name))


TEXT_EXTENSIONS = {
    ".java", ".kt", ".smali", ".xml", ".json", ".txt", ".md", ".html",
    ".js", ".css", ".properties", ".yml", ".yaml", ".gradle", ".pro",
    ".cfg", ".ini", ".log", ".sh", ".py", ".manifest"
}


def view_text_file(path: Path) -> None:
    """Abre arquivos de texto no próprio terminal, com paginação quando disponível."""
    try:
        if path.stat().st_size > 5 * 1024 * 1024:
            print(YELLOW + t("view.too_large") + RESET)
            print(t("folder.path", path=path))
            return
        content = path.read_text(encoding="utf-8", errors="replace")
        clean = sanitize(content)
        less = shutil.which("less")
        if less:
            # Sem -R: não interpretamos códigos de escape do arquivo, só mostramos como texto.
            # Um arquivo decompilado/extraído é conteúdo não confiável.
            subprocess.run([less], input=clean, text=True, check=False)
            return
        lines = clean.splitlines()
        page_size = 120
        for start in range(0, max(1, len(lines)), page_size):
            print("\n".join(lines[start:start + page_size]))
            if start + page_size < len(lines):
                answer = safe_input("\n" + t("view.next_page")).strip().lower()
                if answer in ("q", "s", "ç"):
                    break
        if not lines:
            print(t("view.empty"))
    except (OSError, UnicodeError) as exc:
        print(RED + t("view.open_error", error=exc) + RESET)


def browse_directory(path: Path, allowed_roots: tuple[Path, ...]) -> None:
    """Navegador simples: seleciona diretórios e abre arquivos pelo número."""
    current = path.resolve()
    roots = tuple(root.resolve() for root in allowed_roots)
    while True:
        print(CYAN + "\n" + t("browse.title", path=current) + RESET)
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            print(RED + t("browse.list_error", error=exc) + RESET)
            return
        if not entries:
            print(t("browse.empty"))
        for index, item in enumerate(entries, 1):
            kind = "[DIR] " if item.is_dir() else "[ARQ] "
            try:
                size = f" ({item.stat().st_size / 1024:.1f} KB)" if item.is_file() else "/"
            except OSError:
                size = ""
            print(f" [{index}] {kind}{sanitize(item.name)}{size}")
        print(t("browse.nav"))
        choice = safe_input(t("browse.prompt")).strip().lower()
        if is_exit(choice):
            return
        if choice in {"..", "p", "voltar", "geri", "‹", "<"}:
            if current in roots:
                return
            parent = current.parent.resolve()
            if not any(parent == root or root in parent.parents for root in roots):
                return
            current = parent
            continue
        try:
            selected = entries[int(choice) - 1].resolve()
        except (ValueError, IndexError):
            print(YELLOW + t("browse.invalid") + RESET)
            continue
        if not any(selected == root or root in selected.parents for root in roots):
            print(RED + t("browse.blocked") + RESET)
            continue
        if selected.is_dir():
            current = selected
        elif selected.is_file():
            if selected.suffix.lower() in TEXT_EXTENSIONS or selected.suffix == "":
                view_text_file(selected)
            elif shutil.which("termux-open"):
                print(t("browse.opening"))
                result = subprocess.run([shutil.which("termux-open"), str(selected)], check=False)
                if result.returncode:
                    print(t("browse.cannot_open", path=selected))
            else:
                print(t("browse.no_termux_open", path=selected))
                print(t("browse.install_tools"))
            safe_input("\n" + t("browse.back"))


def browse_generated_files() -> None:
    """Permite localizar e abrir saídas do JADX/Apktool, builds e relatórios JSON."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    BUILDS.mkdir(parents=True, exist_ok=True)
    while True:
        print(CYAN + "\n" + t("gen.title") + RESET)
        print(t("gen.output"))
        print(t("gen.reports"))
        print(t("gen.builds"))
        print(t("gen.back"))
        choice = safe_input(t("browse.prompt")).strip()
        if is_exit(choice):
            return
        if choice == "1":
            browse_directory(OUTPUTS, (OUTPUTS, REPORTS, BUILDS))
        elif choice == "2":
            browse_directory(REPORTS, (OUTPUTS, REPORTS, BUILDS))
        elif choice == "3":
            browse_directory(BUILDS, (OUTPUTS, REPORTS, BUILDS))
        else:
            print(YELLOW + t("gen.invalid") + RESET)


# ------------------------------------------------------------------ reconstrução e compilação

def prompt_rename_package(decoded: Path) -> None:
    """Pergunta o novo applicationId, valida e aplica. Usado nos dois fluxos
    (opção 10 isolada e dentro da opção 11, antes de reconstruir)."""
    print(DIM + t("rename.intro1") + RESET)
    print(DIM + t("rename.intro2") + RESET)
    new_name = safe_input(t("rename.prompt")).strip()
    if not new_name:
        return
    if not valid_package_name(new_name):
        print(RED + t("rename.invalid") + RESET)
        return
    result = rename_package(decoded, new_name)
    if result["ok"]:
        print(GREEN + result["message"] + RESET)
        if result["directories_moved"] or result["files_updated"]:
            print(t("rename.moved", dirs=result['directories_moved'], files=result['files_updated']))
        if result.get("warning"):
            print(YELLOW + result["warning"] + RESET)
    else:
        print(RED + result["message"] + RESET)


def quick_edits_menu() -> None:
    decoded = ask_decoded_dir()
    if decoded is None:
        return
    keys = list(QUICK_EDIT_KEYS)
    print(CYAN + "\n" + t("quick.title") + RESET)
    for i, k in enumerate(keys, 1):
        print(f" [{i}] {t('builder.edit.' + k)}")
    choice = safe_input(t("quick.prompt")).strip()
    chosen = []
    for part in choice.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(keys):
            chosen.append(keys[int(part) - 1])
    if chosen:
        result = apply_quick_edits(decoded, chosen)
        if result["ok"]:
            print(GREEN + t("quick.applied", items=", ".join(result["applied"])) + RESET)
        else:
            print(RED + result["message"] + RESET)
    elif choice:
        print(YELLOW + t("quick.invalid") + RESET)

    if is_yes(safe_input(t("quick.ask_rename"))):
        prompt_rename_package(decoded)
    print(t("quick.hint"))


def rebuild_and_sign() -> None:
    print(CYAN + "\n" + t("build.title") + RESET)
    print(YELLOW + t("build.warn1") + RESET)
    print(DIM + t("build.warn2") + RESET)
    decoded = ask_decoded_dir()
    if decoded is None:
        return
    if not (decoded / "AndroidManifest.xml").is_file() or not (decoded / "apktool.yml").is_file():
        print(YELLOW + t("build.not_apktool") + RESET)
        if not is_yes(safe_input(t("build.continue"))):
            return

    edits: list[str] = []
    if is_yes(safe_input(t("build.ask_quick"))):
        keys = list(QUICK_EDIT_KEYS)
        for i, k in enumerate(keys, 1):
            print(f" [{i}] {t('builder.edit.' + k)}")
        choice = safe_input(t("quick.prompt_short")).strip()
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(keys):
                edits.append(keys[int(part) - 1])

    if is_yes(safe_input(t("build.ask_rename"))):
        prompt_rename_package(decoded)

    name = decoded.name.replace("_apktool", "") or "app"
    work_dir = BUILDS / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def say(msg: str) -> None:
        print(CYAN + " · " + msg + RESET)

    result = build_pipeline(decoded, work_dir, KEYSTORE, DEFAULT_ALIAS, DEFAULT_STOREPASS, edits, say)
    steps = result["steps"]
    for step_name, label in (("quick_edits", t("build.step.quick")),
                             ("rebuild", t("build.step.rebuild")),
                             ("align", t("build.step.align")),
                             ("keystore", t("build.step.keystore")),
                             ("sign", t("build.step.sign")),
                             ("verify", t("build.step.verify"))):
        step = steps.get(step_name)
        if not step:
            continue
        ok = step.get("ok")
        mark = (GREEN + "OK" + RESET if ok
                else (YELLOW + t("build.step.skipped") + RESET if step.get("skipped")
                      else RED + t("build.step.failed") + RESET))
        print(f" [{mark}] {label}")
        if step.get("message"):
            print("      " + step["message"])
        if step.get("warning"):
            print(YELLOW + "      " + step["warning"] + RESET)
        if not ok and step.get("stderr"):
            print(DIM + "      " + step["stderr"][-400:] + RESET)

    if result["ok"]:
        final = Path(result["final_apk"])
        print(GREEN + "\n" + t("build.ready", path=final) + RESET)
        print("SHA256:", steps.get("sha256", "?"))
        # Facilita achar no celular: também copiamos pra Downloads, se liberado.
        downloads = Path.home() / "storage" / "downloads"
        if downloads.is_dir():
            dest = downloads / "ReaDroid" / final.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(final, dest)
            print(GREEN + t("build.copy", path=dest) + RESET)
        if shutil.which("termux-open") and is_yes(safe_input(t("build.ask_open"))):
            subprocess.run([shutil.which("termux-open"), str(final)], check=False)
    else:
        print(RED + "\n" + t("build.incomplete") + RESET)


def keystore_menu() -> None:
    print(CYAN + "\n" + t("keys.title") + RESET)
    if KEYSTORE.is_file():
        print(t("keys.in_use", path=KEYSTORE))
        print(t("keys.alias", alias=DEFAULT_ALIAS))
        print(t("keys.default_pass"))
        if is_yes(safe_input(t("keys.ask_delete"))):
            KEYSTORE.unlink()
            print(GREEN + t("keys.deleted") + RESET)
    else:
        print(t("keys.none_yet"))
        print(t("keys.location", path=KEYSTORE))
    if shutil.which("apksigner") and KEYSTORE.is_file():
        print(DIM + t("keys.tip") + RESET)


# ------------------------------------------------------------------ menu

MENU = [
    ("1", "menu.inspect"),
    ("2", "menu.manifest"),
    ("3", "menu.strings"),
    ("4", "menu.jadx"),
    ("5", "menu.apktool"),
    ("6", "menu.deps"),
    ("7", "menu.reports_dir"),
    ("8", "menu.output_dir"),
    ("9", "menu.explore"),
    ("10", "menu.quick"),
    ("11", "menu.build"),
    ("12", "menu.keystore"),
]


def print_menu() -> None:
    for key, label in MENU:
        print(f" [{key}] {t(label)}")
    print(t("menu.exit"))


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    BUILDS.mkdir(parents=True, exist_ok=True)
    while True:
        banner()
        print_menu()
        choice = safe_input(CYAN + "\nReaDroid > " + RESET).strip()

        if choice == "1":
            run_action("inspection", inspect_apk)
        elif choice == "2":
            run_action("manifest", lambda apk: analyze_manifest(apk, OUTPUTS / (apk.stem + "_manifest_work")))
        elif choice == "3":
            run_action("strings", scan_strings)
        elif choice == "4":
            apk = ask_apk()
            if apk:
                target = OUTPUTS / (apk.stem + "_jadx")
                print(YELLOW + t("jadx.warn") + RESET)
                if is_yes(safe_input(t("ui.save_at", target=target))):
                    result = decompile_with_jadx(apk, target)
                    print((GREEN if result.get("ok") else YELLOW) + result.get("message", t("ui.done")) + RESET)
                    print(t("ui.dest", path=result.get("output_dir", target)))
                    if result.get("stderr"):
                        print(sanitize(result["stderr"][-2500:]))
                    save_and_show(result, "jadx", apk)
        elif choice == "5":
            apk = ask_apk()
            if apk:
                target = OUTPUTS / (apk.stem + "_apktool")
                print(YELLOW + t("apktool.warn") + RESET)
                if is_yes(safe_input(t("ui.save_at", target=target))):
                    result = extract_smali_with_apktool(apk, target)
                    print((GREEN if result.get("ok") else YELLOW) + result.get("message", t("ui.done")) + RESET)
                    print(t("ui.dest", path=result.get("output_dir", target)))
                    if result.get("stderr"):
                        print(sanitize(result["stderr"][-2500:]))
                    save_and_show(result, "apktool", apk)
                    if result.get("ok"):
                        print(DIM + t("apktool.edit_hint") + RESET)
        elif choice == "6":
            dependencies()
        elif choice == "7":
            open_folder(REPORTS)
        elif choice == "8":
            open_folder(OUTPUTS)
        elif choice == "9":
            browse_generated_files()
        elif choice == "10":
            quick_edits_menu()
        elif choice == "11":
            rebuild_and_sign()
        elif choice == "12":
            keystore_menu()
        elif choice in ("0", ""):
            print(GREEN + t("ui.bye") + RESET)
            break
        else:
            print(YELLOW + t("ui.unknown_option") + RESET)
        if choice != "0":
            pause()