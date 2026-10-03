"""Riepilogo stampabile della posizione.

--- COSA FA QUESTO FILE ---
Definisce l'indirizzo `/stampa`: una pagina pulita, sempre in tema chiaro, con
tutto ciò che descrive la posizione aperta (mercato, gambe, numeri chiave,
grafico, greche). Il pulsante «Stampa / Salva PDF» apre la finestra di stampa
del browser, dove si può scegliere «Salva come PDF».

Così non serve nessuna libreria per creare PDF: li fa già il browser, e il
risultato è identico a ciò che si vede.
"""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from ... import __version__ as app_version
from ...pricing import StockLeg, moneyness
from .. import auth, session
from ..chart import build_payoff_option
from ..formatting import format_money, format_number, format_percent, format_signed_money
from ..layout import APP_NAME
from ..state import compute
from ..strategies import STRATEGIES
from ..theme import apply_theme, chart_palette
from ..widgets import CARD, FAINT, card_title, didactic_notice, stat

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


@ui.page("/stampa")
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
                "Stampa / Salva PDF",
                icon="print",
                on_click=lambda: ui.run_javascript("window.print()"),
            ).props("unelevated no-caps")
            ui.label("Nella finestra di stampa scegli «Salva come PDF».").classes("text-xs t-muted")

        with ui.row().classes("w-full items-end justify-between gap-4"):
            with ui.column().classes("gap-0"):
                ui.label(f"{APP_NAME} di opzioni · riepilogo").classes("sim-eyebrow")
                ui.label(f"{state.ticker} · {state.name}").classes("sim-h1")
                if strategy is not None:
                    ui.label(strategy.name).classes("text-sm t-muted")
            ui.label(datetime.now().strftime("%d/%m/%Y %H:%M")).classes("text-xs t-muted")

        with ui.card().classes(CARD):
            card_title("Mercato", "tune")
            with ui.row().classes("w-full gap-6 flex-wrap"):
                m = state.market
                _kv("Spot", format_money(m.spot, cur))
                _kv("Giorni alla scadenza", format_number(m.days_to_expiry, 0))
                _kv("Volatilità implicita", format_percent(m.iv, 1))
                _kv("Tasso risk-free", format_percent(m.risk_free_rate, 2))
                _kv("Dividend yield", format_percent(m.dividend_yield, 2))
                _kv("Esercizio", "europeo" if state.exercise == "european" else "americano")

        with ui.element("div").classes("w-full grid gap-2 grid-cols-2 sm:grid-cols-5"):
            debit = a.net_cost >= 0
            stat(
                "Costo / credito",
                format_signed_money(-a.net_cost, cur),
                tone="loss" if debit else "profit",
            )
            stat("Profitto massimo", format_signed_money(a.max_profit, cur), tone="profit")
            stat("Perdita massima", format_signed_money(a.max_loss, cur), tone="loss")
            stat(
                "Break-even",
                "  ·  ".join(format_number(b, 2) for b in a.break_evens) or "nessuno",
            )
            stat("Prob. di profitto", format_percent(a.prob_profit, 1))

        with ui.card().classes(CARD + " p-2"):
            ui.echart(build_payoff_option(state, a, chart_palette("light"))).classes(
                "w-full h-[360px]"
            )

        with ui.card().classes(CARD):
            card_title("Gambe", "stacked_line_chart")
            with ui.row().classes("w-full gap-2 no-wrap sim-thead px-1"):
                for text, width in [
                    ("Gamba", "grow"),
                    ("Strike / carico", "w-28 text-right"),
                    ("Q.tà", "w-14 text-right"),
                    ("Premio", "w-24 text-right"),
                    ("", "w-14 text-right"),
                ]:
                    ui.label(text).classes(width)
            for leg in state.legs:
                stock = isinstance(leg, StockLeg)
                label = (
                    f"{leg.side.title()} azione" if stock else f"{leg.side.title()} {leg.right}"  # type: ignore[union-attr]
                )
                reference = leg.entry_price if stock else leg.strike  # type: ignore[union-attr]
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
            card_title("Greche aggregate", "functions")
            g = a.greeks
            with ui.row().classes("w-full gap-6 flex-wrap"):
                _kv("Δ Delta", format_number(g.delta, 4))
                _kv("Γ Gamma", format_number(g.gamma, 4))
                _kv("Θ Theta $/gg", format_number(g.theta_per_day, 4))
                _kv("ν Vega $/1% IV", format_number(g.vega_per_point, 4))
                _kv("ρ Rho $/1% tasso", format_number(g.rho_per_point, 4))
            ui.label(
                f"Costo reale: {format_signed_money(-a.cost.net, cur)} per "
                f"{state.sizing.packages} pacchett{'o' if state.sizing.packages == 1 else 'i'} "
                f"(moltiplicatore {format_number(state.sizing.contract_multiplier, 0)})."
            ).classes(FAINT + " mt-2")

        didactic_notice()
        ui.label(f"Generato con {APP_NAME} di opzioni {app_version}.").classes(
            "text-[11px] t-faint"
        )
