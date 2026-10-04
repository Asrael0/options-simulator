"""Lingua dell'interfaccia: italiano o inglese.

--- COSA FA QUESTO FILE ---
Il testo dell'interfaccia è scritto nel codice in italiano. Ogni frase che
l'utente vede passa da ``tr()``: in italiano la restituisce com'è, in inglese
la cerca nel dizionario di ``lang_en.py``.

Le frasi con parti variabili usano segnaposto fra graffe, come in
``str.format``:

    tr("Fra {days} gg", days=12)  ->  "Fra 12 gg"  /  "In 12 days"

La chiave del dizionario è sempre la frase italiana con i segnaposto, così
leggendo il codice si capisce subito cosa compare a schermo. Un test controlla
che ogni frase passata a ``tr()`` abbia la sua traduzione.

La scelta si salva nel browser, come tema e colore; cambiare lingua ricarica
la pagina.
"""

from __future__ import annotations

from typing import Any, Literal

from nicegui import app, ui

Lang = Literal["it", "en"]
LANG_STORAGE_KEY = "lang"
DEFAULT_LANG: Lang = "it"
LANGUAGES: dict[str, str] = {"it": "Italiano", "en": "English"}


def current_lang() -> Lang:
    """Lingua scelta dal visitatore; italiano fuori da una pagina (test, thread)."""
    try:
        stored = app.storage.user.get(LANG_STORAGE_KEY)
    except (RuntimeError, AssertionError):
        return DEFAULT_LANG
    return "en" if stored == "en" else "it"


def set_lang(lang: str) -> None:
    """Cambia lingua e ricarica la pagina."""
    if lang in LANGUAGES:
        app.storage.user[LANG_STORAGE_KEY] = lang
        ui.navigate.reload()


def tr(text: str, /, **values: Any) -> str:
    """Frase nella lingua corrente, con i segnaposto riempiti."""
    template = text
    if current_lang() == "en":
        from .lang_en import EN

        template = EN.get(text, text)
    return template.format(**values) if values else template


def trn(singular: str, plural: str, count: int | float, /, **values: Any) -> str:
    """Come ``tr``, scegliendo la frase al singolare o al plurale.

    ``{n}`` nella frase diventa il numero: ``trn("{n} gamba", "{n} gambe", 3)``.
    """
    return tr(singular if count == 1 else plural, n=_number(count), **values)


def _number(count: int | float) -> str:
    return str(int(count)) if float(count).is_integer() else str(count)
