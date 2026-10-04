"""The simulator page.

Defines the ``/`` route: a single page with the position always in view
(market, strategies, summary, chart) and, under the chart, the analysis tabs:
legs, Greeks, scenarios, P&L map, costs and the chart legend.

Tabs switch without reloading the page: there is a single state, so editing a
leg already updates the open tab.
"""

from __future__ import annotations

from functools import partial

from nicegui import app, ui

from .. import auth, session
from ..chart import build_heatmap_option, build_payoff_option
from ..context import PageContext
from ..i18n import tr
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
)
from ..state import compute_heatmap
from ..theme import chart_palette
from ..widgets import CARD, FAINT, card_title

CHART_CLASSES = "w-full h-[480px]"
HEATMAP_CLASSES = "w-full h-[460px]"

SPLIT = "w-full gap-4 items-stretch no-wrap max-lg:flex-wrap"
SIDE = "gap-4 grow-0 shrink-0 w-full lg:w-[360px] sim-fill-col"
MAIN = "gap-4 grow min-w-0 sim-fill-col"
TAB_PANEL = "p-0 pt-5 gap-4 flex flex-col"

# Tabs under the chart: internal name -> (label, icon). The open tab is
# remembered per user, so it is still open after a reload.
TABS: dict[str, tuple[str, str]] = {
    "legs": ("Gambe", "stacked_line_chart"),
    "greeks": ("Greche", "functions"),
    "scenarios": ("Scenari", "science"),
    "map": ("Mappa P&L", "grid_on"),
    "costs": ("Costi", "receipt_long"),
    "legend": ("Legenda", "help_outline"),
}
TAB_STORAGE_KEY = "simulator_tab_v3"


def _context() -> PageContext | None:
    """Page context, or ``None`` when the user is not logged in.

    Returning ``None`` instead of raising lets the page write
    ``if ctx is None: return`` and quietly stop: ``require_login`` has already
    ordered the redirect to the login page.
    """
    if not auth.require_login():
        return None
    info = session.touch(auth.current_username())
    session.STATS.page_views += 1
    return PageContext(info.position)


def _chart_legend() -> None:
    """Chart explanation: fixed text, independent of the position."""
    with ui.card().classes(CARD):
        card_title(tr("Come si legge il grafico"), "help_outline")
        ui.label(
            tr(
                "La linea bianca è il risultato a scadenza: è la spezzata che conta "
                "davvero, perché è il P&L che realizzi se tieni la posizione fino "
                "alla fine. La linea viola tratteggiata è il valore oggi, alla "
                "volatilità corrente: è più liscia perché al valore intrinseco si "
                "somma ancora del valore temporale. Man mano che i giorni passano, "
                "la viola scende verso la bianca."
            )
        ).classes(FAINT)
        ui.label(
            tr(
                "L'area verde è profitto, la rossa è perdita, e i confini cadono "
                "esattamente sui break-even. Le linee verticali tratteggiate in "
                "arancione sono gli strike, quella blu continua è il prezzo spot "
                "attuale, quelle verdi sono i break-even."
            )
        ).classes(FAINT)
        ui.label(
            tr(
                "Se sposti lo slider del tempo sopra il grafico, o imposti nella scheda "
                "«Scenari» una data o una IV diverse da oggi, compare la curva "
                "terracotta «Scenario»: il valore della posizione in quel giorno e con "
                "quella volatilità. La linea verticale terracotta è il prezzo dello "
                "scenario."
            )
        ).classes(FAINT)


@ui.page("/")
def simulator_page() -> None:
    ctx = _context()
    if ctx is None:
        return
    # Controls on the left; key figures, the chart and, below it, the tabs on
    # the right: legs, Greeks, scenarios, map, costs, legend.
    with (
        page_frame(
            "/",
            subtitle=tr("Costruisci una posizione e guarda come reagisce a prezzo, tempo e IV."),
        ),
        ui.row().classes(SPLIT),
    ):
        with ui.column().classes(SIDE):
            ctx.panel(market_panel)
            ctx.panel(strategy_panel)
            ctx.panel(saved_panel)
        with ui.column().classes(MAIN):
            ctx.panel(summary_panel)
            with ui.column().classes("w-full gap-1 sim-chart p-2"):
                ctx.panel(chart_controls_panel)
                ctx.main_chart = ctx.chart(
                    partial(build_payoff_option, palette=chart_palette()), CHART_CLASSES
                )
            _analysis_tabs(ctx)

    ctx.animation = ui.timer(0.35, lambda: _advance_time(ctx), active=False)


def _advance_time(ctx: PageContext) -> None:
    """One animation step: time moves forward up to expiry, then stops."""
    state = ctx.state
    dte = state.market.days_to_expiry
    step = max(1.0, round(dte / 30))
    state.days_forward = min(state.days_forward + step, dte)
    if state.days_forward >= dte and ctx.animation is not None:
        ctx.animation.deactivate()
    ctx.rerender()


def _analysis_tabs(ctx: PageContext) -> None:
    """A single card: the tabs on top and their content below."""
    stored = app.storage.user.get(TAB_STORAGE_KEY)
    current = stored if stored in TABS else next(iter(TABS))
    open_tab = {"name": current}

    def on_tab(name: str) -> None:
        open_tab["name"] = name
        app.storage.user.update({TAB_STORAGE_KEY: name})
        # The map is expensive: it is recomputed only while its tab is open.
        ctx.refresh_charts()

    with ui.column().classes("w-full gap-0 sim-card sim-tabgroup"):
        with (
            ui.tabs(
                # NiceGUI also accepts the tab name, but its type hints only
                # declare the Tab object.
                value=current,  # type: ignore[arg-type]
                on_change=lambda e: on_tab(e.value),
            )
            .props("dense no-caps align=left inline-label")
            .classes("sim-tabs self-start max-w-full") as tabs
        ):
            for name, (label, icon) in TABS.items():
                ui.tab(name, label=tr(label), icon=icon)
        with ui.tab_panels(tabs, value=current, animated=False).classes("w-full bg-transparent"):
            with ui.tab_panel("legs").classes(TAB_PANEL):
                ctx.panel(legs_panel)
            with ui.tab_panel("greeks").classes(TAB_PANEL):
                ctx.panel(greeks_panel)
            with (
                ui.tab_panel("scenarios").classes(TAB_PANEL),
            ):
                ctx.panel(scenario_panel)
            with ui.tab_panel("map").classes(TAB_PANEL):
                ctx.panel(heatmap_intro_panel)
                palette = chart_palette()
                ctx.chart(
                    lambda state, analytics: build_heatmap_option(
                        state, compute_heatmap(state, analytics), palette
                    ),
                    HEATMAP_CLASSES,
                    active=lambda: open_tab["name"] == "map",
                )
            with ui.tab_panel("costs").classes(TAB_PANEL):
                ctx.panel(cost_panel)
            with ui.tab_panel("legend").classes(TAB_PANEL):
                _chart_legend()
