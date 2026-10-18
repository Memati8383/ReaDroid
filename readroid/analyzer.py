"""Rotinas de análise estática. Não instala, executa nem altera o APK analisado."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from . import __version__, axml
from .i18n import t

MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_TOTAL_SCAN_BYTES = 256 * 1024 * 1024
MAX_REPORT_ITEMS = 3000

URL_RE = re.compile(rb"https?://[^\s\x00\"'<>]{4,500}", re.I)
# Lista de TLDs reais (não "qualquer coisa.palavra"), senão nomes de classe Java/Kotlin
# e nomes de arquivo viram "domínio" por acidente (ex.: classes.dex, gate.php).
_TLDS = (rb"com|net|org|io|dev|app|gov|edu|mil|info|biz|name|pro|xyz|top|online|site|club|vip|link|click|"
        rb"shop|store|live|icu|buzz|cyou|work|space|tech|cc|ws|pw|su|me|co|ai|br|ru|cn|tk|ml|ga|cf|gq|"
        rb"onion|duckdns|ngrok")
DOMAIN_RE = re.compile(rb"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + _TLDS + rb")\b")
IPV4_RE = re.compile(rb"(?<![0-9.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9.])")
# Prefixos de pacotes Android/Java/Kotlin que combinam com a forma de um domínio
# ("android.content.pm") mas nunca são um - filtrados antes de entrar no relatório.
_NOT_DOMAIN_PREFIXES = (b"android.", b"androidx.", b"java.", b"javax.", b"kotlin.", b"kotlinx.", b"dalvik.",
                        b"com.android.", b"com.google.android.", b"org.apache.", b"org.json.", b"org.w3c.",
                        b"org.xml.", b"sun.", b"libcore.")

ANDROID_NS = "http://schemas.android.com/apk/res/android"
A = "{" + ANDROID_NS + "}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    # Lemos em blocos para não carregar um APK inteiro na memória.
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], timeout: int = 180) -> dict[str, Any]:
    """Executa uma ferramenta opcional sem passar argumentos por um shell."""
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout, check=False)
        return {"returncode": result.returncode,
                "stdout": result.stdout[-20000:],
                "stderr": result.stderr[-20000:]}
    except FileNotFoundError:
        return {"returncode": None, "stdout": "", "stderr": t("analyzer.err.tool_missing")}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": t("analyzer.err.timeout", seconds=timeout)}
    except OSError as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}


# Extensões que normalmente guardam um ZIP/APK válido. Não é mais um bloqueio rígido:
# o que importa é o conteúdo (zipfile.is_zipfile), a extensão só gera um aviso.
KNOWN_APK_EXTENSIONS = (".apk", ".apks", ".xapk", ".apk.1")


def validate_apk(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise ValueError(t("analyzer.err.path_not_file"))
    if path.stat().st_size == 0:
        raise ValueError(t("analyzer.err.empty"))
    if not zipfile.is_zipfile(path):
        raise ValueError(t("analyzer.err.not_zip"))


def extension_warning(path: Path) -> str | None:
    if path.suffix.lower() not in KNOWN_APK_EXTENSIONS:
        return t("analyzer.warn.extension", ext=path.suffix or t("analyzer.no_extension"))
    return None


def inspect_apk(path: Path) -> dict[str, Any]:
    validate_apk(path)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        dex_files = [name for name in names if re.fullmatch(r"classes(?:\d+)?\.dex", name)]
        native_libs = [name for name in names if name.startswith("lib/") and name.endswith(".so")]
        resource_count = sum(name.startswith("res/") for name in names)
        asset_count = sum(name.startswith("assets/") for name in names)
        manifest_info = next((item for item in infos if item.filename == "AndroidManifest.xml"), None)
        manifest_kind = t("analyzer.manifest.absent")
        if manifest_info:
            try:
                content = archive.read(manifest_info)
                manifest_kind = (t("analyzer.manifest.text_xml") if content.lstrip().startswith(b"<")
                                 else t("analyzer.manifest.binary_xml"))
            except (OSError, RuntimeError, zipfile.BadZipFile):
                manifest_kind = t("analyzer.manifest.unreadable")
        warning = extension_warning(path)
        return {
            "tool": "ReaDroid", "version": __version__,
            "analyzed_at_utc": datetime.now(timezone.utc).isoformat(),
            "file_name": path.name, "file_size_bytes": path.stat().st_size,
            "sha256": sha256_file(path), "zip_entry_count": len(infos),
            "manifest": {"present": manifest_info is not None, "format": manifest_kind},
            "dex_files": dex_files, "native_libraries": native_libs,
            "resource_file_count": resource_count, "asset_file_count": asset_count,
            "file_list_sample": names[:500],
            "warnings": [warning] if warning else [],
            "note": t("analyzer.note.inspect")
        }


def _looks_like_text_xml(data: bytes) -> bool:
    return data.lstrip().startswith(b"<")


def _parse_manifest_xml(data: bytes) -> dict[str, Any]:
    """Extrai campos básicos quando o manifesto está em XML legível."""
    result: dict[str, Any] = {"decoded": False, "permissions": [], "components": [], "application": {}}
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        result["reason"] = t("analyzer.reason.not_text_xml")
        return result
    result["decoded"] = True
    result["package"] = root.attrib.get("package")
    result["version_code"] = root.attrib.get(A + "versionCode")
    result["version_name"] = root.attrib.get(A + "versionName")
    permission_tags = {"uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m"}
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in permission_tags:
            name = node.attrib.get(A + "name") or node.attrib.get("name")
            if name:
                result["permissions"].append({"name": name, "max_sdk": node.attrib.get(A + "maxSdkVersion")})
        if tag == "application":
            result["application"] = {
                "label": node.attrib.get(A + "label"),
                "debuggable": node.attrib.get(A + "debuggable"),
                "allow_backup": node.attrib.get(A + "allowBackup"),
                "uses_cleartext_traffic": node.attrib.get(A + "usesCleartextTraffic")
            }
        if tag in {"activity", "activity-alias", "service", "receiver", "provider"}:
            result["components"].append({
                "type": tag,
                "name": node.attrib.get(A + "name"),
                "exported": node.attrib.get(A + "exported"),
                "permission": node.attrib.get(A + "permission")
            })
    result["permissions"] = sorted(result["permissions"], key=lambda item: item["name"])
    return result


def analyze_manifest(path: Path, output_dir: Path) -> dict[str, Any]:
    validate_apk(path)
    manifest_data = None
    with zipfile.ZipFile(path) as archive:
        try:
            manifest_data = archive.read("AndroidManifest.xml")
        except KeyError:
            pass
    if manifest_data is None:
        raise ValueError(t("analyzer.err.manifest_absent"))

    parsed: dict[str, Any]
    if _looks_like_text_xml(manifest_data):
        parsed = _parse_manifest_xml(manifest_data)
    else:
        # Praticamente todo APK real cai aqui: o manifesto é binário (AXML).
        # Decodificamos nativamente primeiro; só recorremos a JADX/Apktool/aapt2
        # se o nosso parser falhar (manifesto corrompido de propósito, por exemplo).
        try:
            events = axml.parse_events(manifest_data)
            parsed = axml.to_manifest_dict(events)
            parsed["decoded_by"] = t("analyzer.decoded_by.native")
        except axml.AxmlError as exc:
            parsed = {"decoded": False, "permissions": [], "components": [],
                      "reason": t("analyzer.reason.axml_failed", error=exc)}

    tools: dict[str, Any] = {}
    # JADX pode exportar o manifesto decodificado junto dos recursos. A saída é tratada como dado, não como comando.
    jadx = shutil.which("jadx")
    if not parsed.get("decoded") and jadx:
        jadx_out = output_dir / "jadx_manifest"
        result = _run([jadx, "-d", str(jadx_out), "--no-src", str(path)], timeout=240)
        tools["jadx"] = {"returncode": result["returncode"], "stderr": result["stderr"]}
        candidates = [jadx_out / "resources" / "AndroidManifest.xml", jadx_out / "AndroidManifest.xml"]
        for candidate in candidates:
            if candidate.is_file():
                parsed = _parse_manifest_xml(candidate.read_bytes())
                parsed["decoded_by"] = "jadx"
                break

    apktool = shutil.which("apktool")
    if not parsed.get("decoded") and apktool:
        apktool_out = output_dir / "apktool_manifest"
        result = _run([apktool, "d", "-f", "-s", "-o", str(apktool_out), str(path)], timeout=240)
        tools["apktool"] = {"returncode": result["returncode"], "stderr": result["stderr"]}
        candidate = apktool_out / "AndroidManifest.xml"
        if candidate.is_file():
            parsed = _parse_manifest_xml(candidate.read_bytes())
            parsed["decoded_by"] = "apktool"

    # aapt2 pode fornecer ao menos a lista de permissões quando não conseguimos obter XML.
    aapt2 = shutil.which("aapt2")
    if not parsed.get("decoded") and aapt2:
        result = _run([aapt2, "dump", "permissions", str(path)], timeout=120)
        tools["aapt2"] = {"returncode": result["returncode"], "stderr": result["stderr"]}
        permission_names = sorted(set(re.findall(
            r"(?:uses-permission(?:-sdk-\d+)?):\s*(?:name=)?['\"]?([A-Za-z0-9_.]+)",
            result["stdout"] + "\n" + result["stderr"])))
        if permission_names:
            parsed["permissions"] = [{"name": name, "max_sdk": None} for name in permission_names]
            parsed["permissions_source"] = "aapt2 dump permissions"

    parsed["tool"] = "ReaDroid"
    parsed["apk"] = path.name
    parsed["sha256"] = sha256_file(path)
    parsed["optional_tool_runs"] = tools
    parsed["security_note"] = t("analyzer.note.security")
    return parsed


def scan_strings(path: Path) -> dict[str, Any]:
    validate_apk(path)
    found: dict[str, set[str]] = {"urls": set(), "domains": set(), "ipv4_candidates": set()}
    truncated: set[str] = set()  # categorias que bateram no limite (o relatório pode estar incompleto)
    scanned = 0
    skipped_large = 0

    def add(category: str, value: str) -> None:
        bucket = found[category]
        if value in bucket:
            return
        if len(bucket) >= MAX_REPORT_ITEMS:
            truncated.add(category)
            return
        bucket.add(value)

    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            # Limites simples evitam que um APK com arquivos enormes consuma toda a memória.
            if info.file_size > MAX_ENTRY_BYTES:
                skipped_large += 1
                continue
            name = info.filename.lower()
            allowed = (name.endswith((".dex", ".xml", ".arsc", ".so", ".txt", ".json", ".js", ".html", ".properties", ".smali"))
                       or name.startswith("assets/"))
            if not allowed:
                continue
            if scanned >= MAX_TOTAL_SCAN_BYTES:
                break
            try:
                data = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile):
                continue
            remaining = MAX_TOTAL_SCAN_BYTES - scanned
            data = data[:remaining]
            scanned += len(data)
            for item in URL_RE.findall(data):
                add("urls", item.decode("utf-8", "replace"))
            for item in DOMAIN_RE.findall(data):
                low = item.lower()
                if low.startswith(_NOT_DOMAIN_PREFIXES):
                    continue
                add("domains", low.decode("ascii", "replace"))
            for raw in IPV4_RE.findall(data):
                candidate = raw.decode("ascii", "replace")
                try:
                    ipaddress.IPv4Address(candidate)
                    add("ipv4_candidates", candidate)
                except ipaddress.AddressValueError:
                    pass
    return {
        "tool": "ReaDroid", "apk": path.name, "sha256": sha256_file(path),
        "bytes_scanned": scanned, "large_entries_skipped": skipped_large,
        "urls": sorted(found["urls"]),
        "domains": sorted(found["domains"]),
        "ipv4_candidates": sorted(found["ipv4_candidates"]),
        "truncated_categories": sorted(truncated),
        "note": t("analyzer.note.scan")
    }


def decompile_with_jadx(path: Path, output_dir: Path, threads: int = 2) -> dict[str, Any]:
    """Decompila com JADX e distingue sucesso completo, parcial e falha real."""
    validate_apk(path)
    jadx = shutil.which("jadx")
    if not jadx:
        return {"ok": False, "partial": False, "status": "failed",
                "message": t("analyzer.err.no_jadx")}
    output_dir.mkdir(parents=True, exist_ok=True)
    # Limitamos threads para reduzir a pressão sobre a RAM em celulares.
    command = [jadx, "--threads-count", str(max(1, min(threads, 4))), "-d", str(output_dir), str(path)]
    result = _run(command, timeout=900)
    files = [item for item in output_dir.rglob("*") if item.is_file()]
    java_count = sum(item.suffix.lower() == ".java" for item in files)
    resource_count = sum("/resources/" in item.as_posix() or item.parent.name == "resources" for item in files)
    produced_files = len(files)
    returncode = result["returncode"]
    complete = returncode == 0 and produced_files > 0
    partial = produced_files > 0 and not complete
    if complete:
        status = "success"
        message = t("analyzer.jadx.success", files=produced_files, java=java_count)
    elif partial:
        status = "partial"
        message = t("analyzer.jadx.partial", code=returncode, files=produced_files, java=java_count)
    else:
        status = "failed"
        message = t("analyzer.jadx.failed", code=returncode)
    return {"ok": complete, "partial": partial, "status": status,
            "command": command[0:3] + ["…"], "returncode": returncode,
            "output_dir": str(output_dir), "files_generated": produced_files,
            "java_files": java_count, "resource_files": resource_count,
            "stdout": result["stdout"], "stderr": result["stderr"], "message": message}


def extract_smali_with_apktool(path: Path, output_dir: Path) -> dict[str, Any]:
    validate_apk(path)
    apktool = shutil.which("apktool")
    if not apktool:
        return {"ok": False, "message": t("analyzer.err.no_apktool_soft")}
    output_dir.mkdir(parents=True, exist_ok=True)
    result = _run([apktool, "d", "-f", "-o", str(output_dir), str(path)], timeout=900)
    smali_dirs = [str(p) for p in output_dir.glob("smali*") if p.is_dir()]
    return {"ok": result["returncode"] == 0, "returncode": result["returncode"],
            "output_dir": str(output_dir), "smali_directories": smali_dirs,
            "stdout": result["stdout"], "stderr": result["stderr"]}


def write_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
