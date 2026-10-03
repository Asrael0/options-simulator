"""La pagina del simulatore.

--- COSA FA QUESTO FILE ---
Definisce l'indirizzo `/`: una sola pagina con la posizione sempre in vista
(mercato, strategie, gambe, riepilogo, grafico) e, sotto il grafico, le schede
delle analisi: greche, scenari, costi e la legenda del grafico.

Le schede cambiano senza ricaricare la pagina: lo stato è uno solo, quindi
modificando una gamba la scheda aperta è già aggiornata.
"""

from __future__ import annotations

from functools import partial

from nicegui import app, ui

from .. import auth, session
from ..chart import build_payoff_option
from ..context import PageContext
from ..layout import page_frame
from ..panels import (
    cost_panel,
    greeks_panel,
    legs_panel,
    market_panel,
    scenario_panel,
    strategy_panel,
    summary_panel,
    vol_crush_panel,
)
from ..theme import chart_palette
from ..widgets import CARD, FAINT, card_title

CHART_CLASSES = "w-full h-[500px] sim-chart p-2"

SPLIT = "w-full gap-4 items-start no-wrap max-lg:flex-wrap"
SIDE = "gap-4 grow-0 shrink-0 w-full lg:w-[360px]"
MAIN = "gap-4 grow min-w-0"
TAB_PANEL = "p-0 pt-4 gap-4 flex flex-col"

# Schede sotto il grafico: nome interno -> (etichetta, icona). La scheda aperta
# viene ricordata per utente, così ricaricando la pagina si ritrova.
TABS: dict[str, tuple[str, str]] = {
    "greche": ("Greche", "functions"),
    "scenari": ("Scenari", "science"),
    "costi": ("Costi", "receipt_long"),
    "legenda": ("Come si legge", "help_outline"),
}
TAB_STORAGE_KEY = "simulator_tab"


def _context() -> PageContext | None:
    """Contesto della pagina, o ``None`` se l'utente non è autenticato.

    Restituire `None` invece di sollevare un errore permette alla pagina di
    scrivere `if ctx is None: return` e uscire in silenzio: il reindirizzamento
    al login è già stato ordinato da `require_login`.
    """
    if not auth.require_login():
        return None
    info = session.touch(auth.current_username())
    session.STATS.page_views += 1
    return PageContext(info.position)


def _chart_legend() -> None:
    """Spiegazione del grafico: testo fisso, non dipende dalla posizione."""
    with ui.card().classes(CARD):
        card_title("Come si legge il grafico", "help_outline")
        ui.label(
            "La linea bianca è il risultato a scadenza: è la spezzata che conta "
            "davvero, perché è il P&L che realizzi se tieni la posizione fino "
            "alla fine. La linea viola tratteggiata è il valore oggi, alla "
            "volatilità corrente: è più liscia perché al valore intrinseco si "
            "somma ancora del valore temporale. Man mano che i giorni passano, "
            "la viola scende verso la bianca."
        ).classes(FAINT)
        ui.label(
            "L'area verde è profitto, la rossa è perdita, e i confini cadono "
            "esattamente sui break-even. Le linee verticali tratteggiate in "
            "arancione sono gli strike, quella blu continua è il prezzo spot "
            "attuale, quelle verdi sono i break-even."
        ).classes(FAINT)
        ui.label(
            "Se nella scheda «Scenari» imposti una IV simulata diversa da quella "
            "di mercato, compare anche una terza curva punteggiata arancione: è "
            "il valore oggi a quella volatilità. La distanza fra viola e "
            "arancione, a parità di prezzo, è tutta vega."
        ).classes(FAINT)


@ui.page("/")
def simulator_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with (
        page_frame(
            "/",
            subtitle="Costruisci una posizione e guarda come reagisce a prezzo, tempo e IV.",
        ),
        ui.row().classes(SPLIT),
    ):
        # A sinistra i comandi, a destra i risultati: prima i numeri chiave,
        # poi il grafico, poi le gambe che li producono.
        with ui.column().classes(SIDE):
            ctx.panel(market_panel)
            ctx.panel(strategy_panel)
        with ui.column().classes(MAIN):
            ctx.panel(summary_panel)
            ctx.chart(partial(build_payoff_option, palette=chart_palette()), CHART_CLASSES)
            ctx.panel(legs_panel)

            stored = app.storage.user.get(TAB_STORAGE_KEY)
            current = stored if stored in TABS else next(iter(TABS))
            with (
                ui.tabs(
                    # NiceGUI accetta anche il nome della scheda, ma i tipi
                    # dichiarano solo l'oggetto Tab.
                    value=current,  # type: ignore[arg-type]
                    on_change=lambda e: app.storage.user.update({TAB_STORAGE_KEY: e.value}),
                )
                .props("dense no-caps align=left inline-label narrow-indicator")
                .classes("w-full sim-tabs") as tabs
            ):
                for name, (label, icon) in TABS.items():
                    ui.tab(name, label=label, icon=icon)
            with ui.tab_panels(tabs, value=current, animated=False).classes(
                "w-full bg-transparent"
            ):
                with ui.tab_panel("greche").classes(TAB_PANEL):
                    ctx.panel(greeks_panel)
                with ui.tab_panel("scenari").classes(TAB_PANEL):
                    ctx.panel(vol_crush_panel)
                    ctx.panel(scenario_panel)
                with ui.tab_panel("costi").classes(TAB_PANEL):
                    ctx.panel(cost_panel)
                with ui.tab_panel("legenda").classes(TAB_PANEL):
                    _chart_legend()
