"""Interface language: Italian or English.

The interface text is written in the code in Italian, the default language.
Every sentence the user sees goes through ``tr()``: in Italian it is returned
as it is, in English it is looked up in the ``lang_en.py`` dictionary.

Sentences with variable parts use brace placeholders, as in ``str.format``:

    tr("fra {days} gg", days=12)  ->  "fra 12 gg"  /  "in 12 d"

The dictionary key is always the Italian sentence with its placeholders, so the
code shows exactly what appears on screen. ``tests/test_i18n.py`` checks that
every sentence passed to ``tr()`` has a translation with the same placeholders.

The choice is stored in the browser, like theme and colour; changing language
reloads the page.
"""

from __future__ import annotations

from typing import Any, Literal

from nicegui import app, ui

Lang = Literal["it", "en"]
LANG_STORAGE_KEY = "lang"
DEFAULT_LANG: Lang = "it"
LANGUAGES: dict[str, str] = {"it": "Italiano", "en": "English"}


def current_lang() -> Lang:
    """Language chosen by the visitor; Italian outside a page (tests, threads)."""
    try:
        stored = app.storage.user.get(LANG_STORAGE_KEY)
    except (RuntimeError, AssertionError):
        return DEFAULT_LANG
    return "en" if stored == "en" else "it"


def set_lang(lang: str) -> None:
    """Switch language and reload the page."""
    if lang in LANGUAGES:
        app.storage.user[LANG_STORAGE_KEY] = lang
        ui.navigate.reload()


def tr(text: str, /, **values: Any) -> str:
    """Sentence in the current language, with its placeholders filled in."""
    template = text
    if current_lang() == "en":
        from .lang_en import EN

        template = EN.get(text, text)
    return template.format(**values) if values else template


def trn(singular: str, plural: str, count: int | float, /, **values: Any) -> str:
    """Like ``tr``, picking the singular or plural sentence.

    ``{n}`` in the sentence becomes the number: ``trn("{n} gamba", "{n} gambe", 3)``.
    """
    return tr(singular if count == 1 else plural, n=_number(count), **values)


def _number(count: int | float) -> str:
    return str(int(count)) if float(count).is_integer() else str(count)
