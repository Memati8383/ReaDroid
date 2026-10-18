"""Reconstrução e compilação de APK: apktool b + zipalign + assinatura, automatizado.

A ideia: você usa a opção de extração (Apktool) pra decodificar o APK, edita o
smali/recursos como quiser, e aqui a gente faz o resto - reconstrói, alinha,
assina e confere - pra sair um APK pronto pra instalar, sem decorar comandos.

Isso usa só ferramentas padrão do ecossistema Android (apktool, zipalign,
apksigner/jarsigner), chamadas sempre com lista de argumentos (sem shell).
Nenhum arquivo é enviado pra internet e o projeto original não é alterado.

Use só em APKs seus ou que você tem autorização para modificar. Reassinar um
app troca a identidade do desenvolvedor original: o resultado não substitui
nem atualiza o app da loja, e redistribuir o app de outra pessoa sem permissão
pode violar a licença dele.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .analyzer import _run, sha256_file  # mesmo helper de subprocess já usado no projeto
from .i18n import t

DEFAULT_ALIAS = "readroid"
DEFAULT_STOREPASS = "readroid123"

# Pequenas edições que só fazem sentido numa pasta já decodificada pelo Apktool,
# porque é aí que o AndroidManifest.xml volta a ser texto editável.
# Os rótulos ficam em t("builder.edit.<chave>") e são resolvidos na hora de
# exibir, para que trocar READROID_LANG em tempo de execução faça efeito.
QUICK_EDIT_KEYS = ("debuggable_on", "debuggable_off", "allowbackup_off",
                   "cleartext_on", "add_internet")


def _manifest_path(decoded_dir: Path) -> Path:
    return decoded_dir / "AndroidManifest.xml"


def apply_quick_edits(decoded_dir: Path, edits: list[str]) -> dict[str, Any]:
    manifest = _manifest_path(decoded_dir)
    if not manifest.is_file():
        return {"ok": False, "message": t("builder.err.no_manifest")}
    text = manifest.read_text(encoding="utf-8", errors="replace")
    applied = []

    def set_app_attr(attr: str, value: str) -> None:
        nonlocal text
        pattern = re.compile(rf'android:{attr}="[^"]*"')
        if pattern.search(text):
            text = pattern.sub(f'android:{attr}="{value}"', text, count=1)
        else:
            text = re.sub(r"<application\b", f'<application android:{attr}="{value}"', text, count=1)

    if "debuggable_on" in edits:
        set_app_attr("debuggable", "true")
        applied.append("debuggable=true")
    if "debuggable_off" in edits:
        set_app_attr("debuggable", "false")
        applied.append("debuggable=false")
    if "allowbackup_off" in edits:
        set_app_attr("allowBackup", "false")
        applied.append("allowBackup=false")
    if "cleartext_on" in edits:
        set_app_attr("usesCleartextTraffic", "true")
        applied.append("usesCleartextTraffic=true")
    if "add_internet" in edits and "android.permission.INTERNET" not in text:
        text = re.sub(
            r"(<manifest\b[^>]*>)",
            r'\1\n    <uses-permission android:name="android.permission.INTERNET"/>',
            text, count=1,
        )
        applied.append(t("builder.edit.applied.internet"))
    manifest.write_text(text, encoding="utf-8")
    return {"ok": True, "applied": applied, "manifest": str(manifest)}


_PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")


def valid_package_name(name: str) -> bool:
    """Formato do Android: segmentos separados por ponto, cada um começando com
    letra, pelo menos dois segmentos (com.exemplo, não só exemplo)."""
    return bool(_PACKAGE_RE.match(name))


def rename_package(decoded_dir: Path, new_package: str) -> dict[str, Any]:
    """Renomeia o applicationId (pacote) de um APK já decodificado pelo Apktool.

    Isso é 'melhor esforço': reescreve o manifesto, MOVE as pastas smali do
    pacote antigo para o novo (o código Android é organizado em pastas que
    espelham o nome do pacote) e troca as referências de classe dentro dos
    arquivos .smali, nas duas formas que aparecem (com ponto e com barra, tipo
    smali: "Lcom/exemplo/app/MainActivity;"). Reflection, nomes de pacote
    montados em runtime ou ofuscação pesada podem escapar da substituição -
    sempre teste o APK reconstruído antes de confiar nele.
    """
    manifest = _manifest_path(decoded_dir)
    if not manifest.is_file():
        return {"ok": False, "message": t("builder.err.no_manifest")}
    if not valid_package_name(new_package):
        return {"ok": False, "message": t("builder.err.invalid_package")}

    text = manifest.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'package="([^"]+)"', text)
    if not match:
        return {"ok": False, "message": t("builder.err.no_package_attr")}
    old_package = match.group(1)
    if old_package == new_package:
        return {"ok": True, "old_package": old_package, "new_package": new_package,
                "directories_moved": 0, "files_updated": 0,
                "message": t("builder.rename.same")}

    old_path, new_path = old_package.replace(".", "/"), new_package.replace(".", "/")

    # 1) manifesto: troca o atributo package=
    text = text.replace(f'package="{old_package}"', f'package="{new_package}"', 1)
    manifest.write_text(text, encoding="utf-8")

    # 2) move as pastas smali (pode haver várias com multidex: smali, smali_classes2...)
    directories_moved = 0
    for smali_root in sorted(decoded_dir.glob("smali*")):
        if not smali_root.is_dir():
            continue
        old_dir = smali_root / old_path
        if not old_dir.is_dir():
            continue
        new_dir = smali_root / new_path
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        if new_dir.exists():
            # a pasta de destino já existe (outro smali_classesN criou antes) - mescla o conteúdo
            for item in old_dir.iterdir():
                shutil.move(str(item), str(new_dir / item.name))
            old_dir.rmdir()
        else:
            shutil.move(str(old_dir), str(new_dir))
        directories_moved += 1
        # limpa as pastas do caminho antigo que ficaram vazias
        parent = old_dir.parent
        while parent != smali_root and parent.is_dir() and not any(parent.iterdir()):
            empty, parent = parent, parent.parent
            empty.rmdir()

    # 3) troca as referências ao pacote dentro do código (forma com ponto e forma smali/com barra)
    # Lookahead só proíbe outra LETRA/NÚMERO logo depois (pra não confundir "com.x.app"
    # com "com.x.app2"); um ponto depois é permitido de propósito, porque é assim que o
    # pacote aparece como prefixo de uma classe totalmente qualificada
    # (ex.: android:name="com.x.app.MainActivity" deve virar "com.novo.pacote.MainActivity").
    dotted_re = re.compile(r"(?<![\w.])" + re.escape(old_package) + r"(?!\w)")
    slashed_re = re.compile(re.escape("L" + old_path + "/"))
    files_updated = 0
    for smali_file in decoded_dir.rglob("*.smali"):
        try:
            content = smali_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        updated = slashed_re.sub("L" + new_path + "/", content)
        updated = dotted_re.sub(new_package, updated)
        if updated != content:
            smali_file.write_text(updated, encoding="utf-8")
            files_updated += 1

    # o manifesto pode citar o pacote de novo em outros atributos (android:name relativo etc.)
    manifest_text = manifest.read_text(encoding="utf-8", errors="replace")
    updated_manifest = dotted_re.sub(new_package, manifest_text)
    if updated_manifest != manifest_text:
        manifest.write_text(updated_manifest, encoding="utf-8")

    return {"ok": True, "old_package": old_package, "new_package": new_package,
            "directories_moved": directories_moved, "files_updated": files_updated,
            "message": t("builder.rename.done", old=old_package, new=new_package),
            "warning": t("builder.rename.best_effort")}


def ensure_keystore(keystore_path: Path, alias: str = DEFAULT_ALIAS,
                    storepass: str = DEFAULT_STOREPASS, keypass: str | None = None) -> dict[str, Any]:
    """Cria uma keystore local se ainda não existir. Nunca sobrescreve uma existente."""
    if keystore_path.is_file():
        return {"ok": True, "created": False, "path": str(keystore_path), "alias": alias}
    keytool = shutil.which("keytool")
    if not keytool:
        return {"ok": False, "created": False,
                "message": t("builder.err.no_keytool")}
    keystore_path.parent.mkdir(parents=True, exist_ok=True)
    dname = "CN=ReaDroid, OU=OffensiveTec, O=OffensiveTec, L=Local, ST=Local, C=BR"
    cmd = [keytool, "-genkeypair", "-keystore", str(keystore_path), "-alias", alias,
           "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
           "-storepass", storepass, "-keypass", keypass or storepass, "-dname", dname]
    result = _run(cmd, timeout=60)
    ok = result["returncode"] == 0 and keystore_path.is_file()
    return {"ok": ok, "created": ok, "path": str(keystore_path), "alias": alias,
            "stderr": result["stderr"] if not ok else ""}


def rebuild_apk(decoded_dir: Path, output_apk: Path) -> dict[str, Any]:
    """apktool b: reconstrói o APK a partir da pasta decodificada (smali + recursos)."""
    apktool = shutil.which("apktool")
    if not apktool:
        return {"ok": False, "message": t("builder.err.no_apktool")}
    if not decoded_dir.is_dir():
        return {"ok": False, "message": t("builder.err.dir_missing", path=decoded_dir)}
    output_apk.parent.mkdir(parents=True, exist_ok=True)
    result = _run([apktool, "b", str(decoded_dir), "-o", str(output_apk)], timeout=600)
    ok = result["returncode"] == 0 and output_apk.is_file()
    return {"ok": ok, "returncode": result["returncode"], "stdout": result["stdout"][-4000:],
            "stderr": result["stderr"][-4000:], "output": str(output_apk)}


def align_apk(in_apk: Path, out_apk: Path) -> dict[str, Any]:
    """zipalign: otimiza o alinhamento dos dados do ZIP. Vem junto do pacote 'aapt' no Termux."""
    zipalign = shutil.which("zipalign")
    if not zipalign:
        return {"ok": False, "skipped": True,
                "message": t("builder.err.no_zipalign")}
    result = _run([zipalign, "-f", "-p", "4", str(in_apk), str(out_apk)], timeout=180)
    ok = result["returncode"] == 0 and out_apk.is_file()
    return {"ok": ok, "skipped": False, "returncode": result["returncode"], "stderr": result["stderr"][-2000:]}


def sign_apk(apk: Path, keystore: Path, alias: str = DEFAULT_ALIAS,
            storepass: str = DEFAULT_STOREPASS, keypass: str | None = None) -> dict[str, Any]:
    """Assina com apksigner (v1+v2+v3, preferido) ou jarsigner (só v1) como alternativa."""
    apksigner = shutil.which("apksigner")
    if apksigner:
        cmd = [apksigner, "sign", "--ks", str(keystore), "--ks-key-alias", alias,
               "--ks-pass", f"pass:{storepass}", "--key-pass", f"pass:{keypass or storepass}", str(apk)]
        result = _run(cmd, timeout=180)
        ok = result["returncode"] == 0
        # Não inventamos o esquema aqui: o apksigner só aplica v1 quando o
        # minSdk do APK pede, e dizer "v1 + v2 + v3" mentia em toda rebuild.
        # Os esquemas reais saem de verify_apk(), que lê o 'apksigner verify'.
        return {"ok": ok, "tool": "apksigner", "returncode": result["returncode"],
                "stderr": result["stderr"][-2000:]}
    jarsigner = shutil.which("jarsigner")
    if jarsigner:
        cmd = [jarsigner, "-sigalg", "SHA256withRSA", "-digestalg", "SHA-256", "-keystore", str(keystore),
               "-storepass", storepass, "-keypass", keypass or storepass, str(apk), alias]
        result = _run(cmd, timeout=180)
        ok = result["returncode"] == 0
        return {"ok": ok, "tool": "jarsigner", "scheme": t("builder.scheme.v1_only"), "returncode": result["returncode"],
                "stderr": result["stderr"][-2000:],
                "warning": t("builder.sign.v1_warning")}
    return {"ok": False, "message": t("builder.err.no_signer")}


# "Verified using v2 scheme (APK Signature Scheme v2): true" - o apksigner
# imprime uma linha por esquema e a resposta é o que vale, não o que pedimos.
_SCHEME_RE = re.compile(r"Verified using (v[\d.]+) scheme[^:]*:\s*(true|false)", re.I)


def verify_apk(apk: Path) -> dict[str, Any]:
    apksigner = shutil.which("apksigner")
    if not apksigner:
        return {"ok": None, "message": t("builder.err.no_apksigner_verify")}
    result = _run([apksigner, "verify", "--verbose", str(apk)], timeout=60)
    schemes = [m.group(1) for m in _SCHEME_RE.finditer(result["stdout"])
               if m.group(2).lower() == "true"]
    return {"ok": result["returncode"] == 0, "schemes": schemes,
            "stdout": result["stdout"][-3000:], "stderr": result["stderr"][-2000:]}


def build_pipeline(decoded_dir: Path, work_dir: Path, keystore: Path, alias: str = DEFAULT_ALIAS,
                   storepass: str = DEFAULT_STOREPASS, quick_edits: list[str] | None = None,
                   progress=None) -> dict[str, Any]:
    """Roda tudo em sequência: edições rápidas (opcional) -> build -> align -> keystore -> sign -> verify."""
    say = progress or (lambda m: None)
    steps: dict[str, Any] = {}
    work_dir.mkdir(parents=True, exist_ok=True)

    if quick_edits:
        say(t("builder.say.quick_edits"))
        steps["quick_edits"] = apply_quick_edits(decoded_dir, quick_edits)

    say(t("builder.say.rebuild"))
    unsigned = work_dir / "unsigned.apk"
    steps["rebuild"] = rebuild_apk(decoded_dir, unsigned)
    if not steps["rebuild"]["ok"]:
        return {"ok": False, "steps": steps, "final_apk": None}

    say(t("builder.say.align"))
    aligned = work_dir / "aligned.apk"
    steps["align"] = align_apk(unsigned, aligned)
    to_sign = aligned if steps["align"].get("ok") else unsigned

    say(t("builder.say.keystore"))
    steps["keystore"] = ensure_keystore(keystore, alias, storepass)
    if not steps["keystore"]["ok"]:
        return {"ok": False, "steps": steps, "final_apk": None}

    say(t("builder.say.sign"))
    steps["sign"] = sign_apk(to_sign, keystore, alias, storepass)
    if not steps["sign"]["ok"]:
        return {"ok": False, "steps": steps, "final_apk": None}

    say(t("builder.say.verify"))
    steps["verify"] = verify_apk(to_sign)
    steps["sha256"] = sha256_file(to_sign)
    return {"ok": True, "steps": steps, "final_apk": str(to_sign)}
