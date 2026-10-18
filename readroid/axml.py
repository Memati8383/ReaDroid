"""Leitor de AndroidManifest.xml binário (AXML), sem dependências externas.

TODO APK real guarda o manifesto nesse formato binário, não como texto. Antes,
o ReaDroid só lia manifestos XML textuais (praticamente nenhum APK de verdade)
e dependia de JADX/Apktool/aapt2 pra qualquer coisa real - ferramentas pesadas
de instalar e rodar no celular. Este módulo decodifica o AXML direto, sem Java.
"""
from __future__ import annotations

import struct
from typing import Any

from .i18n import t

# Quando o nome do atributo não vem como string (manifest compactado/ofuscado),
# ele vem só como um ID de recurso do Android; traduzimos os mais comuns aqui.
_RES_IDS = {
    0x01010003: "name", 0x01010006: "permission", 0x0101000E: "enabled", 0x0101000F: "debuggable",
    0x01010010: "exported", 0x0101020C: "minSdkVersion", 0x01010270: "targetSdkVersion",
    0x0101026C: "maxSdkVersion", 0x01010280: "allowBackup", 0x010104EC: "usesCleartextTraffic",
    0x0101021B: "versionCode", 0x0101021C: "versionName", 0x01010001: "label",
}


class AxmlError(Exception):
    pass


def _string_pool(data: bytes, pos: int) -> list:
    hsize = struct.unpack_from("<H", data, pos + 2)[0]
    count, _styles, flags, s_start = struct.unpack_from("<IIII", data, pos + 8)
    utf8 = bool(flags & 0x100)
    offs = struct.unpack_from("<%dI" % count, data, pos + hsize)
    base = pos + s_start
    out = []
    for o in offs:
        p = base + o
        try:
            if utf8:
                n = data[p]; p += 1
                if n & 0x80:
                    n = ((n & 0x7F) << 8) | data[p]; p += 1
                nb = data[p]; p += 1
                if nb & 0x80:
                    nb = ((nb & 0x7F) << 8) | data[p]; p += 1
                out.append(data[p : p + nb].decode("utf-8", "replace"))
            else:
                n = struct.unpack_from("<H", data, p)[0]; p += 2
                if n & 0x8000:
                    n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, p)[0]; p += 2
                out.append(data[p : p + n * 2].decode("utf-16-le", "replace"))
        except (struct.error, IndexError):
            out.append("")
    return out


def _value(strings: list, raw: int, dtype: int, val: int) -> str:
    if raw != 0xFFFFFFFF:
        return strings[raw] if raw < len(strings) else ""
    if dtype == 0x03:  # TYPE_STRING
        return strings[val] if val < len(strings) else ""
    if dtype == 0x12:  # TYPE_INT_BOOLEAN
        return "true" if val else "false"
    if dtype == 0x10:  # TYPE_INT_DEC
        return str(struct.unpack("<i", struct.pack("<I", val))[0])
    if dtype == 0x11:  # TYPE_INT_HEX
        return f"0x{val:x}"
    if dtype == 0x01:  # TYPE_REFERENCE
        return f"@0x{val:08x}"
    return f"0x{val:x}"


def parse_events(data: bytes) -> list:
    """Devolve a lista de eventos do XML: ('start', tag, {attrs}) ou ('end', tag, None)."""
    if len(data) < 8:
        raise AxmlError(t("axml.err.too_small"))
    if struct.unpack_from("<H", data, 0)[0] != 0x0003:
        raise AxmlError(t("axml.err.no_signature"))
    pos = struct.unpack_from("<H", data, 2)[0]
    strings, res_map, events = [], [], []
    try:
        while pos + 8 <= len(data):
            ctype, chsize, csize = struct.unpack_from("<HHI", data, pos)
            if csize < 8:
                break
            if ctype == 0x0001:  # RES_STRING_POOL_TYPE
                strings = _string_pool(data, pos)
            elif ctype == 0x0180:  # RES_XML_RESOURCE_MAP_TYPE
                res_map = list(struct.unpack_from("<%dI" % ((csize - chsize) // 4), data, pos + chsize))
            elif ctype == 0x0102:  # RES_XML_START_ELEMENT_TYPE
                name_idx = struct.unpack_from("<I", data, pos + 20)[0]
                attr_start, attr_size, attr_count = struct.unpack_from("<HHH", data, pos + 24)
                tag = strings[name_idx] if name_idx < len(strings) else "?"
                attrs = {}
                for i in range(attr_count):
                    a = pos + 16 + attr_start + i * attr_size
                    _ns, n_idx, raw, _sz, _r0, dtype, val = struct.unpack_from("<IIIHBBI", data, a)
                    name = strings[n_idx] if n_idx < len(strings) else ""
                    if not name and n_idx < len(res_map):
                        name = _RES_IDS.get(res_map[n_idx], f"res_{res_map[n_idx]:08x}")
                    attrs[name] = _value(strings, raw, dtype, val)
                events.append(("start", tag, attrs))
            elif ctype == 0x0103:  # RES_XML_END_ELEMENT_TYPE
                name_idx = struct.unpack_from("<I", data, pos + 20)[0]
                events.append(("end", strings[name_idx] if name_idx < len(strings) else "?", None))
            pos += csize
    except (struct.error, IndexError) as exc:
        raise AxmlError(t("axml.err.truncated", error=exc)) from exc
    if not events:
        raise AxmlError(t("axml.err.no_events"))
    return events


def events_to_xml(events: list) -> str:
    """Reconstrói um XML legível a partir dos eventos - o manifesto 'recuperado'."""
    lines, depth = [], 0
    for kind, tag, attrs in events:
        if kind == "start":
            parts = []
            for k, v in attrs.items():
                v = v.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
                parts.append(f'{k}="{v}"' if k in ("package",) else f'android:{k}="{v}"')
            lines.append("  " * depth + f"<{tag} {' '.join(parts)}>".replace(" >", ">"))
            depth += 1
        else:
            depth = max(depth - 1, 0)
            lines.append("  " * depth + f"</{tag}>")
    return "\n".join(lines)


def to_manifest_dict(events: list) -> dict[str, Any]:
    """Converte os eventos no mesmo formato que o parser de XML textual já produzia,
    pra o resto do ReaDroid (app.py, relatórios) não precisar saber qual caminho rodou."""
    result: dict[str, Any] = {"decoded": True, "permissions": [], "components": [], "application": {}}
    stack: list[str] = []
    for kind, tag, attrs in events:
        if kind == "end":
            if stack:
                stack.pop()
            continue
        parent = stack[-1] if stack else None
        stack.append(tag)
        if tag == "manifest":
            result["package"] = attrs.get("package")
            result["version_code"] = attrs.get("versionCode")
            result["version_name"] = attrs.get("versionName")
        elif tag in ("uses-permission", "uses-permission-sdk-23", "uses-permission-sdk-m"):
            name = attrs.get("name")
            if name:
                result["permissions"].append({"name": name, "max_sdk": attrs.get("maxSdkVersion")})
        elif tag == "application":
            result["application"] = {
                "label": attrs.get("label"), "debuggable": attrs.get("debuggable"),
                "allow_backup": attrs.get("allowBackup"),
                "uses_cleartext_traffic": attrs.get("usesCleartextTraffic"),
            }
        elif tag in ("activity", "activity-alias", "service", "receiver", "provider") and parent == "application":
            result["components"].append({
                "type": tag, "name": attrs.get("name"),
                "exported": attrs.get("exported"), "permission": attrs.get("permission"),
            })
    result["permissions"] = sorted(result["permissions"], key=lambda item: item["name"])
    return result
