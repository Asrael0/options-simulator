"""Le pagine del simulatore.

--- COSA FA QUESTO FILE ---
Definisce cinque indirizzi web: `/`, `/payoff`, `/greche`, `/scenari`,
`/costi`. Ognuna costruisce un `PageContext` sulla posizione dell'utente e
sceglie quali pannelli mostrare, senza reimplementarli.

Lo stato è condiviso: modificando una gamba dalla pagina «Posizione» e
passando a «Greche», i numeri sono già aggiornati.
"""

from __future__ import annotations

from nicegui import ui

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
from ..widgets import CARD, FAINT, TITLE

CHART_CLASSES = "w-full h-[440px] bg-[#11141c] border border-[#1e222d] rounded-xl p-2"

SPLIT = "w-full gap-4 items-start no-wrap max-lg:flex-wrap"
SIDE = "gap-4 grow-0 shrink-0 w-full lg:w-[340px]"
MAIN = "gap-4 grow min-w-0"


def _context() -> PageContext | None:
    """Contesto della pagina, o ``None`` se l'utente non è autenticato.

    Restituire `None` invece di sollevare un errore permette a ogni pagina di
    scrivere `if ctx is None: return` e uscire in silenzio: il reindirizzamento
    al login è già stato ordinato da `require_login`.
    """
    if not auth.require_login():
        return None
    info = session.touch(auth.current_username())
    session.STATS.page_views += 1
    return PageContext(info.position)


def _sidebar(ctx: PageContext) -> None:
    ctx.panel(market_panel)
    ctx.panel(strategy_panel)


@ui.page("/")
def position_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with (
        page_frame("/", subtitle="Costruisci la posizione e leggi il riepilogo"),
        ui.row().classes(SPLIT),
    ):
        with ui.column().classes(SIDE):
            _sidebar(ctx)
        with ui.column().classes(MAIN):
            ctx.panel(legs_panel)
            ctx.panel(summary_panel)
            ctx.chart(build_payoff_option, CHART_CLASSES)


@ui.page("/payoff")
def payoff_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with page_frame("/payoff", subtitle="Diagramma di payoff a tutta larghezza"):
        ctx.chart(build_payoff_option, CHART_CLASSES.replace("h-[440px]", "h-[560px]"))
        with ui.card().classes(CARD):
            ui.label("Come si legge").classes(TITLE)
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
                "Se hai attivato il simulatore di vol crush con una IV diversa da "
                "quella di mercato, compare anche una terza curva punteggiata "
                "arancione: è il valore oggi a quella volatilità. La distanza fra "
                "viola e arancione, a parità di prezzo, è tutta vega."
            ).classes(FAINT)
        with ui.row().classes(SPLIT):
            with ui.column().classes(SIDE):
                _sidebar(ctx)
            with ui.column().classes(MAIN):
                ctx.panel(legs_panel)
                ctx.panel(summary_panel)


@ui.page("/greche")
def greeks_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with (
        page_frame("/greche", subtitle="Sensibilità della posizione"),
        ui.row().classes(SPLIT),
    ):
        with ui.column().classes(SIDE):
            _sidebar(ctx)
        with ui.column().classes(MAIN):
            ctx.panel(greeks_panel)
            ctx.panel(summary_panel)
            ctx.chart(build_payoff_option, CHART_CLASSES)


@ui.page("/scenari")
def scenarios_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with (
        page_frame("/scenari", subtitle="Vol crush e prezzo-target a scadenza"),
        ui.row().classes(SPLIT),
    ):
        with ui.column().classes(SIDE):
            _sidebar(ctx)
        with ui.column().classes(MAIN):
            ctx.panel(vol_crush_panel)
            ctx.panel(scenario_panel)
            ctx.chart(build_payoff_option, CHART_CLASSES)


@ui.page("/costi")
def costs_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    with (
        page_frame("/costi", subtitle="Dai prezzi teorici all'esborso reale"),
        ui.row().classes(SPLIT),
    ):
        with ui.column().classes(SIDE):
            _sidebar(ctx)
        with ui.column().classes(MAIN):
            ctx.panel(cost_panel)
            ctx.panel(legs_panel)
            ctx.panel(summary_panel)
