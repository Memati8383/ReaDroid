"""Camada de localização do ReaDroid.

Toda string de interface passa por t(). O texto em português continua no
código como padrão implícito e o catálogo pt.json o declara explicitamente;
locales/tr.json traz a tradução. Sem entrada para READROID_LANG/LANG em
formato "tr", este fork assume o próprio idioma: o padrão é o catálogo do
diretório locales/.

Chaves são semânticas (menu.inspect, analyzer.note.scan), não o texto de
origem: quando o upstream mexer no português, a chave não muda e o merge
não explode. use tools/extract_strings.py para achar literais que escaparam
da tradução.

Identificadores, comentários e docstrings ficam em português de propósito -
é a convenção do upstream (ver CONTRIBUTING.md) e é o que mantém o diff
pequeno contra o original.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parents[1] / "locales"
DEFAULT_LANG = "tr"
FALLBACK_LANG = "pt"

_table: dict[str, str] = {}
_lang: str | None = None


def _is_tr(value: str) -> bool:
    head = value.strip().lower().split(".")[0].split("@")[0]
    return head.replace("_", "-").split("-")[0] == "tr"


def detect() -> str:
    """READROID_LANG > LC_ALL > LC_MESSAGES > LANG > DEFAULT_LANG.

    Um valor explícito sempre vence: READROID_LANG=pt tem que dar português
    mesmo numa máquina turca. Fora disso, este fork é bilíngue e o padrão é o
    CATÁLOGO TURCO - não o fallback. Um LANG=en_US.UTF-8 numa tela de celular
    é o normal, não um pedido de português; devolver "pt" ali fazia o menu
    abrir em português para todo mundo, que é justamente o bug que isto
    corrige.
    """
    explicit = os.environ.get("READROID_LANG", "")
    if explicit.strip():
        return "tr" if _is_tr(explicit) else FALLBACK_LANG
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "")
        if value.strip():
            return "tr" if _is_tr(value) else DEFAULT_LANG
    return DEFAULT_LANG


def active_lang() -> str:
    global _lang
    if _lang is None:
        _lang = detect()
    return _lang


def _load(lang: str) -> dict[str, str]:
    path = CATALOG_DIR / f"{lang}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str) and v}


def reload_for_tests(lang: str | None = None) -> None:
    """Limpa o cache. Usado pela suíte de testes."""
    global _table, _lang
    _table, _lang = {}, lang


def table() -> dict[str, str]:
    global _table
    if not _table:
        _table = _load(active_lang()) or _load(FALLBACK_LANG)
    return _table


def t(key: str, **kw) -> str:
    """Texto da interface. Chave ausente aparece como a própria chave - um
    buraco de tradução tem que ser visível, não silencioso."""
    text = table().get(key, key)
    return text.format(**kw) if kw else text


# ------------------------------------------------------------------ respostas sim/não

# O upstream pergunta s/N. Quem lê "[e/H]" na tradução e responde "e" receberia
# um não silencioso, então aceitamos as duas formas.
YES = {"s", "sim", "yes", "y", "e", "evet"}
NO = {"n", "nao", "não", "no", "h", "hayir", "hayır"}
OTHER_PATH = {"p", "path", "y", "yol"}
EXIT = {"0", "q", "sair", "çık", "çik", "cik", ""}


def is_yes(answer: str) -> bool:
    return answer.strip().lower() in YES


def is_no(answer: str) -> bool:
    return answer.strip().lower() in NO


def is_other_path(answer: str) -> bool:
    """[P] no upstream virou [Y] (yol) na tradução; ambos contam."""
    return answer.strip().lower() in OTHER_PATH


def is_exit(answer: str) -> bool:
    return answer.strip().lower() in EXIT