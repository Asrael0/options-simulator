"""Translations: every sentence passed to tr()/trn() must have an English version."""

from __future__ import annotations

import ast
import re
import string
from datetime import date
from pathlib import Path

import pytest

from options_simulator.app import formatting, i18n
from options_simulator.app.lang_en import EN
from options_simulator.app.layout import HERO_POINTS, NAV_PAGES, SETTINGS_PAGE
from options_simulator.app.panels.greeks import GREEK_ROWS
from options_simulator.app.strategies import (
    CUSTOM_STRATEGY_DESCRIPTION,
    CUSTOM_STRATEGY_NAME,
    STRATEGIES,
)
from options_simulator.app.theme import ACCENTS, MODE_LABELS
from options_simulator.app.tickers import CATALOG

APP_DIR = Path(i18n.__file__).parent
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def _needs_translation(text: str) -> bool:
    """Sentences made only of placeholders and symbols are the same in every language."""
    return bool(re.search(r"[A-Za-zÀ-ÿ]", PLACEHOLDER.sub("", text)))


def _literal_keys(node: ast.expr) -> list[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _literal_keys(node.body) + _literal_keys(node.orelse)
    return []


def _keys_in_code() -> dict[str, str]:
    """Sentence -> module, for every tr()/trn()/MarketDataError with a literal text."""
    found: dict[str, str] = {}
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            count = {"tr": 1, "trn": 2, "MarketDataError": 1}.get(name, 0)
            for arg in node.args[:count]:
                for key in _literal_keys(arg):
                    if _needs_translation(key):
                        found.setdefault(key, path.name)
    return found


def _fields(text: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}


def test_every_tr_key_has_an_english_translation() -> None:
    missing = {key: where for key, where in _keys_in_code().items() if key not in EN}
    assert not missing, f"Sentences without an English translation: {missing}"


def test_constants_shown_through_tr_are_translated() -> None:
    texts = [
        *(label for page in [*NAV_PAGES, SETTINGS_PAGE] for label in (page[1], page[3])),
        *(text for _, head, body in HERO_POINTS for text in (head, body)),
        *(label for label, _ in MODE_LABELS.values()),
        *(accent["label"] for accent in ACCENTS.values()),
        *(text for _, name, _, unit, desc in GREEK_ROWS for text in (name, unit, desc)),
        CUSTOM_STRATEGY_NAME,
        CUSTOM_STRATEGY_DESCRIPTION,
        *(text for s in STRATEGIES.values() for text in (s.name, s.description)),
        *CATALOG,
    ]
    missing = [text for text in texts if text and text not in EN]
    assert not missing, f"Constants without an English translation: {missing}"


def test_translations_keep_the_same_placeholders() -> None:
    wrong = {key: value for key, value in EN.items() if _fields(key) != _fields(value)}
    assert not wrong, f"Placeholders differ between Italian and English: {wrong}"


@pytest.fixture
def english(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n, "current_lang", lambda: "en")
    monkeypatch.setattr(formatting, "current_lang", lambda: "en")


def test_italian_is_the_default_outside_a_page() -> None:
    assert i18n.current_lang() == "it"
    assert i18n.tr("Gambe") == "Gambe"
    assert i18n.trn("{n} gamba", "{n} gambe", 2) == "2 gambe"


@pytest.mark.usefixtures("english")
def test_english_texts_and_plurals() -> None:
    assert i18n.tr("Gambe") == "Legs"
    assert i18n.trn("{n} gamba", "{n} gambe", 1) == "1 leg"
    assert i18n.trn("{n} gamba", "{n} gambe", 3) == "3 legs"
    assert i18n.tr("Frase che non esiste") == "Frase che non esiste"


@pytest.mark.usefixtures("english")
def test_english_number_and_date_formats() -> None:
    assert formatting.format_number(1234.5) == "1,234.50"
    assert formatting.format_percent(0.3) == "30%"
    assert formatting.format_date(date(2026, 10, 12)) == "12 Oct 2026"
    assert formatting.format_short_date(date(2026, 10, 12)) == "12 Oct"


def test_italian_number_and_date_formats() -> None:
    assert formatting.format_number(1234.5) == "1.234,50"
    assert formatting.format_date(date(2026, 10, 12)) == "12/10/2026"
    assert formatting.format_short_date(date(2026, 10, 12), year=True) == "12/10/26"
