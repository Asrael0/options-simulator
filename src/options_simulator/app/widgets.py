"""Elementi visivi riutilizzabili e costanti di stile.

--- COSA FA QUESTO FILE ---
Piccoli pezzi di interfaccia usati ovunque: uno slider che non intasa il
server, il riquadro con una cifra in evidenza, l'avviso sui prezzi, e le
costanti dei colori e delle classi CSS.

Sta tutto qui per una ragione sola: se domani i riquadri devono cambiare
aspetto, si modifica un punto invece di quindici.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui
from nicegui.elements.mixins.value_element import ValueElement

from .tickers import (
    CATEGORY_TONES,
    canonical_symbol,
    company_name,
    display_symbol,
    search,
)

CARD = "w-full sim-card"
TITLE = "sim-card-title mb-2"
MUTED = "text-xs t-muted"
FAINT = "text-[12px] t-faint leading-relaxed"
NOTICE = "w-full text-[11px] leading-relaxed px-1 pt-4 mt-4 sim-notice"
DANGER = "w-full text-xs leading-relaxed px-4 py-3 sim-danger"
DANGER_STRIP = "w-full items-center gap-3 no-wrap text-xs px-3 py-2 sim-danger"

# Colori come variabili CSS: il valore vero dipende dal tema (vedi theme.py).
COLOR_PROFIT = "var(--profit)"
COLOR_LOSS = "var(--loss)"
COLOR_NEUTRAL = "var(--text)"

MONEYNESS_COLOR = {
    "ITM": COLOR_PROFIT,
    "OTM": COLOR_LOSS,
    "ATM": "var(--warn)",
    "STOCK": "var(--muted)",
}


# Colore del riquadro dell'icona, deciso dall'icona stessa: così ogni tipo di
# sezione ha sempre lo stesso colore in tutto il sito.
ICON_TONES: dict[str, str] = {
    "tune": "blue",
    "travel_explore": "blue",
    "help_outline": "blue",
    "badge": "blue",
    "dns": "blue",
    "upload_file": "blue",
    "auto_awesome": "violet",
    "functions": "violet",
    "compare_arrows": "violet",
    "terminal": "violet",
    "science": "teal",
    "memory": "teal",
    "query_stats": "teal",
    "flag": "teal",
    "bookmarks": "amber",
    "bookmark_add": "amber",
    "grid_on": "amber",
    "devices": "amber",
    "school": "amber",
    "receipt_long": "red",
    "key": "red",
    "insights": "green",
    "group": "green",
    "account_balance_wallet": "green",
    "fact_check": "violet",
    "inventory_2": "blue",
    "add_shopping_cart": "green",
}


def card_title(
    title: str,
    icon: str,
    *,
    subtitle: str = "",
    action: tuple[str, str, Callable[[], object]] | None = None,
    tone: str | None = None,
) -> None:
    """Intestazione di una card: icona in un riquadro colorato, titolo e,
    a destra, un pulsante opzionale ``(etichetta, icona, azione)``."""
    chosen = tone or ICON_TONES.get(icon, "accent")
    with ui.row().classes("w-full items-center gap-3 no-wrap mb-3"):
        with ui.element("div").classes(f"sim-card-icon tone-{chosen}"):
            ui.icon(icon, size="18px")
        with ui.column().classes("gap-0 grow min-w-0"):
            ui.label(title).classes("sim-card-title")
            if subtitle:
                ui.label(subtitle).classes("text-xs t-muted")
        if action is not None:
            label, action_icon, on_click = action
            ui.button(label, icon=action_icon, on_click=on_click).props(
                "unelevated dense no-caps color=primary"
            ).classes("text-xs px-3 shrink-0")


def ticker_search(
    *,
    label: str,
    value: str = "",
    on_pick: Callable[[str], Any],
    classes: str = "",
    commit_on_blur: bool = False,
    mode: str = "symbol",
    on_text: Callable[[str], Any] | None = None,
    align_right: bool = False,
) -> ui.input:
    """Casella con suggerimenti dal catalogo, che compaiono solo mentre si scrive.

    Si cerca sia per simbolo sia per nome dell'azienda; al massimo sette
    risultati, i più pertinenti in cima, con il colore della loro categoria.

    ``mode`` decide cosa resta scritto nel campo dopo la scelta: il simbolo
    (``"symbol"``) o il nome dell'azienda (``"name"``). In entrambi i casi
    ``on_pick`` riceve il simbolo, nella forma interna (``_SPX``).

    Invio sceglie il risultato che coincide con il testo, o il primo. Se nessun
    titolo corrisponde (o si è premuto Esc): in modalità simbolo il testo vale
    come simbolo (qualunque simbolo USA funziona); in modalità nome va a
    ``on_text`` come nome libero. Con ``commit_on_blur`` anche uscire dal campo conferma.

    ``on_pick`` può essere asincrona: il suo risultato viene restituito
    all'evento, e NiceGUI lo attende.
    """
    matches: list[tuple[str, str, str]] = []

    with ui.element("div").classes("relative " + classes):
        field = ui.input(label, value=value).props("dense outlined").classes("w-full")
        menu = ui.column().classes(
            "sim-suggest absolute top-full mt-1 z-50 gap-0 p-1 w-[340px] max-w-[90vw] "
            + ("right-0" if align_right else "left-0")
        )
        menu.set_visibility(False)

    committed = {"text": value}

    def pick(symbol: str, name: str = "") -> Any:
        menu.set_visibility(False)
        shown = (
            (name or company_name(symbol) or display_symbol(symbol))
            if mode == "name"
            else (display_symbol(symbol))
        )
        field.value = shown
        committed["text"] = shown
        return on_pick(canonical_symbol(symbol))

    def free_text(text: str) -> Any:
        menu.set_visibility(False)
        committed["text"] = text
        if mode == "name":
            return on_text(text) if on_text is not None else None
        return pick(text)

    def show(text: str) -> None:
        nonlocal matches
        matches = search(text)
        menu.clear()
        if not matches:
            menu.set_visibility(False)
            return
        with menu:
            for symbol, name, category in matches:
                tone = CATEGORY_TONES.get(category, "accent")
                with (
                    ui.row()
                    .classes(f"w-full items-center gap-3 no-wrap sim-suggest-item tone-{tone}")
                    .on("mousedown", lambda _, s=symbol, n=name: pick(s, n))
                ):
                    ui.label(display_symbol(symbol)).classes("sim-tone-badge")
                    ui.label(name).classes("text-sm t-text grow truncate")
                    ui.label(category).classes("text-[11px] t-faint shrink-0 max-sm:hidden")
        menu.set_visibility(True)

    def submit() -> Any:
        text = (field.value or "").strip()
        if not text:
            return None
        wanted = text.upper()
        exact = [
            m
            for m in matches
            if display_symbol(m[0]) == display_symbol(text) or m[1].upper() == wanted
        ]
        if exact:
            return pick(exact[0][0], exact[0][1])
        if matches:
            return pick(matches[0][0], matches[0][1])
        return free_text(text)

    def dismiss() -> None:
        # Esc chiude i suggerimenti e li dimentica: Invio salva il testo libero.
        nonlocal matches
        matches = []
        menu.set_visibility(False)

    def leave() -> Any:
        menu.set_visibility(False)
        text = (field.value or "").strip()
        if commit_on_blur and text and text != committed["text"]:
            return free_text(text)
        return None

    field.on("update:model-value", lambda e: show(str(e.args or "")), throttle=0.15)
    field.on("keydown.enter", submit)
    field.on("keydown.esc", dismiss)
    # Il clic su un suggerimento usa «mousedown», che arriva prima del «blur»:
    # chiudere il menu al blur non fa quindi perdere la scelta.
    field.on("blur", leave)
    return field


def throttled_slider(
    *,
    minimum: float,
    maximum: float,
    step: float,
    value: float,
    on_value: Callable[[float], None],
    throttle: float = 0.08,
) -> ui.slider:
    """Slider che non inonda il server di eventi durante il trascinamento.

    Senza throttle un trascinamento produce decine di eventi al secondo, e in
    modalità americana ognuno costruisce alberi binomiali. ``trailing_events``
    garantisce che l'ultimo valore arrivi comunque, quindi non si perde la
    posizione finale del cursore.
    """
    slider = ui.slider(min=minimum, max=maximum, step=step, value=value).props("dense")
    slider.on(
        "update:model-value",
        lambda e: on_value(float(e.args)),
        throttle=throttle,
        trailing_events=True,
    )
    return slider


def commit_on_leave[E: ValueElement[Any]](element: E, on_commit: Callable[..., None]) -> E:
    """Applica il valore di un campo solo con Invio o uscendo dal campo.

    Ogni modifica ridisegna i pannelli, campo compreso: se il valore venisse
    applicato a ogni tasto, il campo verrebbe ricreato e perderebbe il cursore
    dopo una sola cifra. Uscire senza aver cambiato nulla non ricalcola.
    """
    committed = element.value

    def commit() -> None:
        nonlocal committed
        if element.value == committed:
            return
        committed = element.value
        on_commit(element.value)

    element.on("blur", commit)
    element.on("keydown.enter", commit)
    return element


def stat(label: str, value: str, *, tone: str = "neutral", sub: str = "", icon: str = "") -> None:
    """Riquadro con una cifra in evidenza."""
    color = {"profit": COLOR_PROFIT, "loss": COLOR_LOSS}.get(tone, COLOR_NEUTRAL)
    with ui.column().classes("gap-1 sim-stat"):
        with ui.row().classes("items-center gap-1.5 no-wrap"):
            if icon:
                ui.icon(icon, size="15px").style(f"color: {color}")
            ui.label(label).classes("sim-stat-label")
        ui.label(value).classes("sim-stat-value").style(f"color: {color}")
        if sub:
            ui.label(sub).classes("text-[11px] t-faint")


def didactic_notice() -> None:
    """Avviso che deve restare visibile in ogni pagina dell'applicazione."""
    ui.html(
        "<strong>Nota sui prezzi.</strong> I prezzi sono <em>teorici</em>: i modelli "
        "assumono volatilità costante e assenza di salti di prezzo (gap), quindi "
        "divergono dai prezzi reali di mercato. Lo strumento serve a capire le "
        "relazioni tra le variabili, non a stimare prezzi di trading, e non "
        "costituisce consulenza finanziaria."
    ).classes(NOTICE)
