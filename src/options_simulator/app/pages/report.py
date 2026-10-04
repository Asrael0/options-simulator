"""Printable position summary.

Defines the ``/print`` route: a clean page, always in the light theme, with
everything describing the open position (market, legs, key figures, chart,
Greeks). The «Print / Save PDF» button opens the browser's print dialog, where
«Save as PDF» can be chosen.

No PDF library is needed: the browser already makes PDFs, and the result looks
exactly like the page.
"""

from __future__ import annotations

from datetime import UTC, datetime

from nicegui import ui

from ... import __version__ as app_version
from ...pricing import StockLeg, moneyness
from .. import auth, session
from ..chart import build_payoff_option
from ..formatting import (
    format_money,
    format_number,
    format_percent,
    format_signed_money,
    format_timestamp,
)
from ..i18n import tr, trn
from ..state import compute
from ..strategies import STRATEGIES
from ..theme import apply_theme, chart_palette
from ..widgets import CARD, FAINT, card_title, price_notice, stat

PRINT_CSS = """
@media print {
  .no-print { display: none !important; }
  body { background: #ffffff !important; }
  .sim-card { box-shadow: none !important; break-inside: avoid; }
  .nicegui-content { padding: 0 !important; }
}
@page { size: A4; margin: 12mm; }
"""


def _kv(label: str, value: str) -> None:
    with ui.column().classes("gap-0 min-w-[110px]"):
        ui.label(label).classes("sim-stat-label")
        ui.label(value).classes("text-sm t-text t-num")


@ui.page("/print")
def report_page() -> None:
    if not auth.require_login():
        return
    apply_theme(force="light")
    ui.add_css(PRINT_CSS)

    state = session.touch(auth.current_username()).position
    a = compute(state)
    cur = state.currency
    strategy = STRATEGIES.get(state.strategy_key)

    with ui.column().classes("w-full max-w-[860px] mx-auto px-4 py-8 gap-4"):
        with ui.row().classes("w-full items-center gap-2 no-print"):
            ui.button(
                tr("Stampa / Salva PDF"),
                icon="print",
                on_click=lambda: ui.run_javascript("window.print()"),
            ).props("unelevated no-caps")
            ui.label(tr("Nella finestra di stampa scegli «Salva come PDF».")).classes(
                "text-xs t-muted"
            )

        with ui.row().classes("w-full items-end justify-between gap-4"):
            with ui.column().classes("gap-0"):
                ui.label(tr("Simulatore di opzioni · riepilogo")).classes("sim-eyebrow")
                ui.label(tr("{ticker} · {name}", ticker=state.ticker, name=state.name)).classes(
                    "sim-h1"
                )
                if strategy is not None:
                    ui.label(tr(strategy.name)).classes("text-sm t-muted")
            ui.label(format_timestamp(datetime.now(UTC).isoformat())).classes("text-xs t-muted")

        with ui.card().classes(CARD):
            card_title(tr("Mercato"), "tune")
            with ui.row().classes("w-full gap-6 flex-wrap"):
                m = state.market
                _kv(tr("Spot"), format_money(m.spot, cur))
                _kv(tr("Giorni alla scadenza"), format_number(m.days_to_expiry, 0))
                _kv(tr("Volatilità implicita"), format_percent(m.iv, 1))
                _kv(tr("Tasso risk-free"), format_percent(m.risk_free_rate, 2))
                _kv(tr("Dividend yield"), format_percent(m.dividend_yield, 2))
                _kv(
                    tr("Esercizio"),
                    tr("europeo") if state.exercise == "european" else tr("americano"),
                )
                jumps = state.active_jumps
                _kv(
                    tr("Modello di prezzo"),
                    "Black-Scholes"
                    if jumps is None
                    else tr(
                        "Merton: {count} salti/anno di {size}",
                        count=format_number(jumps.intensity, 2),
                        size=format_percent(jumps.expected_jump, 1),
                    ),
                )

        with ui.element("div").classes("w-full grid gap-2 grid-cols-2 sm:grid-cols-5"):
            debit = a.net_cost >= 0
            stat(
                tr("Costo / credito"),
                format_signed_money(-a.net_cost, cur),
                tone="loss" if debit else "profit",
            )
            stat(tr("Profitto massimo"), format_signed_money(a.max_profit, cur), tone="profit")
            stat(tr("Perdita massima"), format_signed_money(a.max_loss, cur), tone="loss")
            stat(
                tr("Break-even"),
                "  ·  ".join(format_number(b, 2) for b in a.break_evens) or tr("nessuno"),
            )
            stat(tr("Prob. di profitto"), format_percent(a.prob_profit, 1))

        with ui.card().classes(CARD + " p-2"):
            ui.echart(build_payoff_option(state, a, chart_palette("light"))).classes(
                "w-full h-[360px]"
            )

        with ui.card().classes(CARD):
            card_title(tr("Gambe"), "stacked_line_chart")
            with ui.row().classes("w-full gap-2 no-wrap sim-thead px-1"):
                for text, width in [
                    ("Gamba", "grow"),
                    ("Strike / carico", "w-28 text-right"),
                    ("Q.tà", "w-14 text-right"),
                    ("Premio", "w-24 text-right"),
                    ("", "w-14 text-right"),
                ]:
                    ui.label(tr(text) if text else "").classes(width)
            for leg in state.legs:
                side = tr(leg.side.title())
                if isinstance(leg, StockLeg):
                    label = tr("{side} azione", side=side)
                    reference = leg.entry_price
                else:
                    label = f"{side} {tr(leg.right)}"
                    reference = leg.strike
                with ui.row().classes(
                    "w-full gap-2 no-wrap text-sm t-text2 t-num py-1.5 sim-divider px-1"
                ):
                    ui.label(label).classes("grow")
                    ui.label(format_number(reference, 2)).classes("w-28 text-right")
                    ui.label(format_number(leg.qty, 0)).classes("w-14 text-right")
                    ui.label(format_money(a.entry_premiums.get(leg.leg_id, 0.0), cur)).classes(
                        "w-24 text-right"
                    )
                    ui.label(moneyness(leg, state.market.spot)).classes("w-14 text-right text-xs")

        with ui.card().classes(CARD):
            card_title(tr("Greche aggregate"), "functions")
            g = a.greeks
            with ui.row().classes("w-full gap-6 flex-wrap"):
                _kv(tr("Δ Delta"), format_number(g.delta, 4))
                _kv(tr("Γ Gamma"), format_number(g.gamma, 4))
                _kv(tr("Θ Theta $/gg"), format_number(g.theta_per_day, 4))
                _kv(tr("ν Vega $/1% IV"), format_number(g.vega_per_point, 4))
                _kv(tr("ρ Rho $/1% tasso"), format_number(g.rho_per_point, 4))
            ui.label(
                tr(
                    "Costo reale: {signed_money} {packages} "
                    "(moltiplicatore {contract_multiplier}).",
                    signed_money=format_signed_money(-a.cost.net, cur),
                    packages=trn("per {n} pacchetto", "per {n} pacchetti", state.sizing.packages),
                    contract_multiplier=format_number(state.sizing.contract_multiplier, 0),
                )
            ).classes(FAINT + " mt-2")

        price_notice()
        ui.label(
            tr(
                "Generato con il simulatore di opzioni, versione {app_version}.",
                app_version=app_version,
            )
        ).classes("text-[11px] t-faint")
