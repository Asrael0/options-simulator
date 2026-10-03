"""Elementi visivi riutilizzabili e costanti di stile.

--- COSA FA QUESTO FILE ---
Piccoli pezzi di interfaccia usati ovunque: uno slider che non intasa il
server, il riquadro con una cifra in evidenza, l'avviso didattico, e le
costanti dei colori e delle classi CSS.

Sta tutto qui per una ragione sola: se domani i riquadri devono cambiare
aspetto, si modifica un punto invece di quindici.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui
from nicegui.elements.mixins.value_element import ValueElement

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


def card_title(
    title: str,
    icon: str,
    *,
    subtitle: str = "",
    action: tuple[str, str, Callable[[], None]] | None = None,
) -> None:
    """Intestazione di una card: icona in un riquadro colorato, titolo e,
    a destra, un pulsante opzionale ``(etichetta, icona, azione)``."""
    with ui.row().classes("w-full items-center gap-3 no-wrap mb-3"):
        with ui.element("div").classes("sim-card-icon"):
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
        "<strong>Nota didattica.</strong> I prezzi sono <em>teorici</em>: i modelli "
        "assumono volatilità costante e assenza di salti di prezzo (gap), quindi "
        "divergono dai prezzi reali di mercato. Lo strumento serve a capire le "
        "relazioni tra le variabili, non a stimare prezzi di trading, e non "
        "costituisce consulenza finanziaria."
    ).classes(NOTICE)
