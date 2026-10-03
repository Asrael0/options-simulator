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
from ..chart import build_heatmap_option, build_payoff_option
from ..context import PageContext
from ..layout import page_frame
from ..panels import (
    chart_controls_panel,
    cost_panel,
    greeks_panel,
    heatmap_intro_panel,
    legs_panel,
    market_panel,
    saved_panel,
    scenario_panel,
    strategy_panel,
    summary_panel,
    vol_crush_panel,
)
from ..state import compute_heatmap
from ..theme import chart_palette
from ..widgets import CARD, FAINT, card_title

CHART_CLASSES = "w-full h-[480px]"
HEATMAP_CLASSES = "w-full h-[460px]"

SPLIT = "w-full gap-4 items-start no-wrap max-lg:flex-wrap"
SIDE = "gap-4 grow-0 shrink-0 w-full lg:w-[360px]"
MAIN = "gap-4 grow min-w-0"
TAB_PANEL = "p-0 pt-5 gap-4 flex flex-col"

# Schede sotto il grafico: nome interno -> (etichetta, icona). La scheda aperta
# viene ricordata per utente, così ricaricando la pagina si ritrova.
TABS: dict[str, tuple[str, str]] = {
    "greche": ("Greche", "functions"),
    "scenari": ("Scenari", "science"),
    "mappa": ("Mappa P&L", "grid_on"),
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
    with page_frame(
        "/",
        subtitle="Costruisci una posizione e guarda come reagisce a prezzo, tempo e IV.",
    ):
        # In alto: a sinistra i comandi, a destra i risultati (numeri chiave,
        # grafico, gambe). Sotto, a tutta larghezza, le analisi di dettaglio.
        with ui.row().classes(SPLIT):
            with ui.column().classes(SIDE):
                ctx.panel(market_panel)
                ctx.panel(strategy_panel)
            with ui.column().classes(MAIN):
                ctx.panel(summary_panel)
                with ui.column().classes("w-full gap-1 sim-chart p-2"):
                    ctx.panel(chart_controls_panel)
                    ctx.main_chart = ctx.chart(
                        partial(build_payoff_option, palette=chart_palette()), CHART_CLASSES
                    )
                ctx.panel(legs_panel)
                ctx.panel(saved_panel)

        _analysis_tabs(ctx)

    ctx.animation = ui.timer(0.35, lambda: _advance_time(ctx), active=False)


def _advance_time(ctx: PageContext) -> None:
    """Un passo dell'animazione: il tempo avanza fino alla scadenza, poi si ferma."""
    state = ctx.state
    dte = state.market.days_to_expiry
    step = max(1.0, round(dte / 30))
    state.days_forward = min(state.days_forward + step, dte)
    if state.days_forward >= dte and ctx.animation is not None:
        ctx.animation.deactivate()
    ctx.rerender()


def _analysis_tabs(ctx: PageContext) -> None:
    """Un solo riquadro: le schede in testa e il loro contenuto sotto."""
    stored = app.storage.user.get(TAB_STORAGE_KEY)
    current = stored if stored in TABS else next(iter(TABS))
    open_tab = {"name": current}

    def on_tab(name: str) -> None:
        open_tab["name"] = name
        app.storage.user.update({TAB_STORAGE_KEY: name})
        # La mappa è costosa: si ricalcola solo quando la sua scheda è aperta.
        ctx.refresh_charts()

    with ui.column().classes("w-full gap-0 sim-card sim-tabgroup"):
        with (
            ui.tabs(
                # NiceGUI accetta anche il nome della scheda, ma i tipi
                # dichiarano solo l'oggetto Tab.
                value=current,  # type: ignore[arg-type]
                on_change=lambda e: on_tab(e.value),
            )
            .props("dense no-caps align=left inline-label")
            .classes("sim-tabs self-start max-w-full") as tabs
        ):
            for name, (label, icon) in TABS.items():
                ui.tab(name, label=label, icon=icon)
        with ui.tab_panels(tabs, value=current, animated=False).classes("w-full bg-transparent"):
            with ui.tab_panel("greche").classes(TAB_PANEL):
                ctx.panel(greeks_panel)
            with (
                ui.tab_panel("scenari").classes(TAB_PANEL),
                ui.row().classes("w-full gap-8 no-wrap max-lg:flex-wrap items-start"),
            ):
                with ui.column().classes("grow basis-0 min-w-[280px]"):
                    ctx.panel(vol_crush_panel)
                with ui.column().classes("grow basis-0 min-w-[280px]"):
                    ctx.panel(scenario_panel)
            with ui.tab_panel("mappa").classes(TAB_PANEL):
                ctx.panel(heatmap_intro_panel)
                palette = chart_palette()
                ctx.chart(
                    lambda state, analytics: build_heatmap_option(
                        state, compute_heatmap(state, analytics), palette
                    ),
                    HEATMAP_CLASSES,
                    active=lambda: open_tab["name"] == "mappa",
                )
            with ui.tab_panel("costi").classes(TAB_PANEL):
                ctx.panel(cost_panel)
            with ui.tab_panel("legenda").classes(TAB_PANEL):
                _chart_legend()
