"""Testes da camada de localização.

Cobrem o que quebra em silêncio quando alguém mexe numa tradução:
chave órfã no catálogo, placeholder {x} que não bate com o do português,
vazio esquecido, e as respostas sim/não que gained um segundo idioma.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from readroid import i18n
from readroid.builder import QUICK_EDIT_KEYS
from readroid.app import MENU

SOURCE_DIR = ROOT / "readroid"
PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

# Chaves montadas em tempo de execução, que um grep estático não pega.
DYNAMIC = (
    [f"builder.edit.{key}" for key in QUICK_EDIT_KEYS]
    + [f"action.{key}.title" for key in ("inspection", "manifest", "strings")]
    + [f"build.step.{key}" for key in ("quick", "rebuild", "align", "keystore", "sign", "verify")]
    + [label for _, label in MENU]
)


def load(name: str) -> dict:
    return json.loads((ROOT / "locales" / name).read_text(encoding="utf-8"))


def used_keys() -> set[str]:
    """Chaves passadas a t() como literal, nos módulos e no install.sh."""
    found: set[str] = set()
    pattern = re.compile(r"""t\(\s*f?["']([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)["']""")
    for path in list(SOURCE_DIR.glob("*.py")) + [ROOT / "readroid.py"]:
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            found.add(match.group(1))
    return found


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pt = load("pt.json")
        cls.tr = load("tr.json")

    def test_catalogs_exist_and_are_not_empty(self):
        self.assertGreater(len(self.pt), 100)
        self.assertGreater(len(self.tr), 100)

    def test_both_catalogs_have_the_same_keys(self):
        self.assertEqual(set(self.pt) - set(self.tr), set(),
                         "chaves só em pt.json (faltou traducao)")
        self.assertEqual(set(self.tr) - set(self.pt), set(),
                         "chaves só em tr.json (sobrou chave Morta)")

    def test_no_empty_translations(self):
        for key, value in self.tr.items():
            self.assertTrue(value.strip(), f"traducao vazia em {key}")

    def test_placeholders_match(self):
        for key, pt_value in self.pt.items():
            self.assertEqual(
                sorted(PLACEHOLDER_RE.findall(pt_value)),
                sorted(PLACEHOLDER_RE.findall(self.tr[key])),
                f"placeholders divergentes em {key}")

    def test_every_key_used_in_code_exists(self):
        missing = sorted(k for k in used_keys() | set(DYNAMIC) if k not in self.tr)
        self.assertEqual(missing, [], "chaves usadas no codigo e ausentes no catalogo")

    def test_no_key_left_untranslated(self):
        """Texto idêntico ao português geralmente significa tradução esquecida.
        Exceções: termos técnicos que coincidem em ambos os idiomas."""
        allow_same = {"banner.watermark"}
        same = {k for k in self.pt
                if k not in allow_same and self.pt[k] == self.tr[k]
                and not PLACEHOLDER_RE.search(self.pt[k])
                and self.pt[k].strip()}
        # Relatórios de erro de ferramental ficam só em pt propositalmente? Não:
        # tudo que o usuário vê foi traduzido. Este teste é o guarda-corpo.
        self.assertEqual(same, set(), "chaves com texto ainda em português")

    def test_placeholders_render(self):
        i18n.reload_for_tests("tr")
        try:
            out = i18n.t("report.zip_summary", files=12, dex=2, libs=1)
            self.assertIn("12", out)
            self.assertNotIn("{", out)
        finally:
            i18n.reload_for_tests("pt")


class LanguageDetectionTests(unittest.TestCase):
    LOCALE_VARS = ("READROID_LANG", "LC_ALL", "LC_MESSAGES", "LANG")

    def setUp(self):
        self._saved = {v: os.environ.get(v) for v in self.LOCALE_VARS}
        for var in self.LOCALE_VARS:
            os.environ.pop(var, None)

    def tearDown(self):
        for var, value in self._saved.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        i18n.reload_for_tests(None)

    def test_readroid_lang_tr(self):
        os.environ["READROID_LANG"] = "tr"
        self.assertEqual(i18n.detect(), "tr")

    def test_readroid_lang_pt(self):
        os.environ["READROID_LANG"] = "pt"
        self.assertEqual(i18n.detect(), "pt")

    def test_lc_all_tr(self):
        os.environ["LC_ALL"] = "tr_TR.UTF-8"
        self.assertEqual(i18n.detect(), "tr")

    def test_readroid_lang_wins_over_locale(self):
        os.environ["LC_ALL"] = "tr_TR.UTF-8"
        os.environ["READROID_LANG"] = "pt"
        self.assertEqual(i18n.detect(), "pt")

    def test_no_locale_uses_fork_default(self):
        self.assertEqual(i18n.detect(), "tr")

    def test_foreign_locale_uses_fork_default_not_fallback(self):
        """Regressão: um LANG=en_US.UTF-8 (o padrão de fábrica do Termux) fazia
        o menu abrir em português para todo mundo. O fork é bilíngue e o padrão
        é o catálogo turco; português exige READROID_LANG=pt."""
        for locale in ("en_US.UTF-8", "C", "pt_BR.UTF-8", "tr_TR", ""):
            os.environ["LANG"] = locale
            self.assertEqual(i18n.detect(), "tr", locale)

    def test_readroid_lang_pt_is_the_only_route_to_portuguese(self):
        os.environ["LANG"] = "en_US.UTF-8"
        os.environ["READROID_LANG"] = "pt"
        self.assertEqual(i18n.detect(), "pt")


class AnswerTests(unittest.TestCase):
    """O menu pergunta sim/não em dois idiomas. 'e' (evet) precisa contar como
    sim, senão o usuário digita o que lê e leva um não."""

    def test_yes_accepts_both_conventions(self):
        for value in ("s", "S", "sim", "e", "E", "evet", " yes "):
            self.assertTrue(i18n.is_yes(value), value)

    def test_no_accepts_both_conventions(self):
        for value in ("n", "N", "nao", "não", "h", "hayir", "hayır"):
            self.assertTrue(i18n.is_no(value), value)

    def test_yes_and_no_do_not_overlap(self):
        self.assertEqual(i18n.YES & i18n.NO, set())

    def test_other_path_accepts_p_and_y(self):
        for value in ("p", "P", "y", "Y", "yol"):
            self.assertTrue(i18n.is_other_path(value), value)

    def test_exit_accepts_empty_and_quit_words(self):
        for value in ("0", "q", "", "sair", "çık"):
            self.assertTrue(i18n.is_exit(value), value)

    def test_number_is_not_a_yes(self):
        self.assertFalse(i18n.is_yes("1"))
        self.assertFalse(i18n.is_yes(""))
        self.assertFalse(i18n.is_no("2"))


class MissingKeyTests(unittest.TestCase):
    def test_unknown_key_shows_itself(self):
        i18n.reload_for_tests("tr")
        try:
            self.assertEqual(i18n.t("nao.existe.mesmo"), "nao.existe.mesmo")
        finally:
            i18n.reload_for_tests("pt")


if __name__ == "__main__":
    unittest.main()