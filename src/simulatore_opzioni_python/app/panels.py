"""Pannelli dell'interfaccia.

Ogni funzione disegna un pannello leggendo il contesto di pagina, e non
calcola nulla di finanziario: i numeri arrivano già pronti da
``ctx.analytics``. Così le pagine si compongono scegliendo quali pannelli
mostrare, senza duplicare logica.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from nicegui import ui

from ..pricing import StockLeg, moneyness
from .context import PageContext
from .formatting import format_money, format_number, format_percent, format_signed_money
from .strategies import STRATEGIES
from .widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    MONEYNESS_COLOR,
    MUTED,
    TITLE,
    stat,
    throttled_slider,
)

#: Simbolo, nome, attributo di ``Greeks``, unità, spiegazione.
GREEK_ROWS: list[tuple[str, str, str, str, str]] = [
    (
        "Δ",
        "Delta",
        "delta",
        "",
        "Variazione del valore della posizione per +1 $ del sottostante. "
        "È l'esposizione direzionale netta.",
    ),
    (
        "Γ",
        "Gamma",
        "gamma",
        "",
        "Variazione del delta per +1 $ del sottostante. Misura quanto "
        "rapidamente cambia l'esposizione direzionale.",
    ),
    (
        "Θ",
        "Theta",
        "theta_per_day",
        "$/gg",
        "Variazione del valore per ogni giorno che passa. Negativo per chi è "
        "net long di opzioni: il tempo erode il premio.",
    ),
    (
        "ν",
        "Vega",
        "vega_per_point",
        "$/1% IV",
        "Variazione del valore per +1 punto di volatilità implicita. Net short "
        "vega guadagna da un vol crush.",
    ),
    (
        "ρ",
        "Rho",
        "rho_per_point",
        "$/1% tasso",
        "Variazione del valore per +1 punto di tasso risk-free. La greca meno "
        "rilevante per scadenze brevi.",
    ),
]


# ---------------------------------------------------------------------------
# Mercato
# ---------------------------------------------------------------------------


def market_panel(ctx: PageContext) -> None:
    state = ctx.state
    m = state.market

    def set_field(name: str, value: Any) -> None:
        if value is None:
            return
        state.set_market(**{name: float(value)})
        ctx.rerender()

    references = [
        leg.entry_price if isinstance(leg, StockLeg) else leg.strike for leg in state.legs
    ]

    with ui.card().classes(CARD):
        ui.label("Sottostante & mercato").classes(TITLE)
        with ui.row().classes("w-full gap-2 no-wrap"):
            ui.input(
                "Ticker",
                value=state.ticker,
                on_change=lambda e: _set_text(ctx, "ticker", e.value),
            ).classes("grow").props("dense outlined")
            ui.input(
                "Nome",
                value=state.name,
                on_change=lambda e: _set_text(ctx, "name", e.value),
            ).classes("grow").props("dense outlined")

        ui.number(
            "Prezzo spot",
            value=m.spot,
            step=0.5,
            format="%.2f",
            on_change=lambda e: set_field("spot", e.value),
        ).classes("w-full").props("dense outlined suffix=$")
        ui.label(f"Spot: {format_number(m.spot, 2)} $").classes(MUTED)
        throttled_slider(
            minimum=max(min(references) * 0.5, 1.0),
            maximum=max(references) * 1.5,
            step=0.5,
            value=m.spot,
            on_value=lambda v: set_field("spot", v),
        ).classes("w-full")

        ui.number(
            "Giorni alla scadenza",
            value=m.days_to_expiry,
            step=1,
            format="%.0f",
            on_change=lambda e: set_field("days_to_expiry", e.value),
        ).classes("w-full").props("dense outlined suffix=gg")
        ui.label(f"Giorni: {format_number(m.days_to_expiry, 0)}").classes(MUTED)
        throttled_slider(
            minimum=0,
            maximum=365,
            step=1,
            value=m.days_to_expiry,
            on_value=lambda v: set_field("days_to_expiry", v),
        ).classes("w-full")

        ui.number(
            "Volatilità implicita (IV)",
            value=m.iv * 100,
            step=1,
            format="%.1f",
            on_change=lambda e: set_field("iv", (e.value or 0) / 100),
        ).classes("w-full").props("dense outlined suffix=%")
        ui.label(f"IV: {format_percent(m.iv, 1)}").classes(MUTED)
        throttled_slider(
            minimum=1,
            maximum=150,
            step=1,
            value=m.iv * 100,
            on_value=lambda v: set_field("iv", v / 100),
        ).classes("w-full")

        with ui.row().classes("w-full gap-2 no-wrap"):
            ui.number(
                "Tasso risk-free",
                value=m.risk_free_rate * 100,
                step=0.25,
                format="%.2f",
                on_change=lambda e: set_field("risk_free_rate", (e.value or 0) / 100),
            ).classes("grow").props("dense outlined suffix=%")
            ui.number(
                "Dividend yield",
                value=m.dividend_yield * 100,
                step=0.25,
                format="%.2f",
                on_change=lambda e: set_field("dividend_yield", (e.value or 0) / 100),
            ).classes("grow").props("dense outlined suffix=%")

        ui.separator().classes("my-2")
        ui.label("Stile di esercizio").classes(MUTED)
        ui.toggle(
            {"european": "Europea", "american": "Americana"},
            value=state.exercise,
            on_change=lambda e: _set_exercise(ctx, e.value),
        ).props("dense").classes("w-full")
        ui.label(
            "Esercitabile solo a scadenza. Prezzata con Black-Scholes-Merton (formula chiusa)."
            if state.exercise == "european"
            else "Esercitabile in qualsiasi momento. Prezzata con albero binomiale "
            "CRR: include il valore dell'esercizio anticipato, visibile "
            "soprattutto sulle put ITM."
        ).classes(FAINT)


def _set_text(ctx: PageContext, attribute: str, value: str) -> None:
    """Ticker e nome non entrano in nessun calcolo: nessun ricalcolo."""
    setattr(ctx.state, attribute, value)
    ctx.rerender()


def _set_exercise(ctx: PageContext, value: str) -> None:
    ctx.state.exercise = value  # type: ignore[assignment]
    ctx.rerender()


# ---------------------------------------------------------------------------
# Strategie e premi d'ingresso
# ---------------------------------------------------------------------------


def strategy_panel(ctx: PageContext) -> None:
    state = ctx.state

    def apply(key: str) -> None:
        state.apply_strategy(key)
        ctx.rerender()

    def set_pin(value: bool) -> None:
        state.set_pin_premiums(value)
        ctx.rerender()

    def reprice() -> None:
        state.reprice_entry()
        ui.notify("Premi rifissati ai prezzi correnti", type="positive")
        ctx.rerender()

    with ui.card().classes(CARD):
        ui.label("Strategie precostruite").classes(TITLE)
        ui.select(
            {key: s.name for key, s in STRATEGIES.items()},
            value=state.strategy_key,
            on_change=lambda e: apply(e.value),
        ).classes("w-full").props("dense outlined")
        ui.label(STRATEGIES[state.strategy_key].description).classes(FAINT)

        ui.separator().classes("my-2")
        ui.label("Premi d'ingresso").classes(MUTED)
        ui.switch(
            "Congelati all'apertura della posizione",
            value=state.pin_premiums,
            on_change=lambda e: set_pin(e.value),
        ).props("dense")
        ui.label(
            "Il costo già pagato non cambia quando muovi lo spot: è il "
            "comportamento corretto. Disattivandolo, i premi vengono riprezzati "
            "ai parametri correnti e la curva «valore oggi» passerà sempre per "
            "lo zero al prezzo spot."
            if state.pin_premiums
            else "I premi seguono i parametri correnti: muovendo lo spot cambia "
            "anche il costo «già pagato», e i break-even scivolano con lo slider."
        ).classes(FAINT)

        if state.pin_premiums:
            entry = state.entry_market
            moved = (
                abs(entry.spot - state.market.spot) > 1e-9
                or abs(entry.iv - state.market.iv) > 1e-12
                or abs(entry.days_to_expiry - state.market.days_to_expiry) > 1e-9
            )
            if moved:
                # Senza questa riga i premi sembrano sbagliati: sono calcolati a
                # un mercato diverso da quello mostrato dagli slider, ed è
                # esattamente ciò che il congelamento promette di fare.
                ui.label(
                    f"Premi fissati a: spot {format_number(entry.spot, 2)} $ · "
                    f"IV {format_percent(entry.iv, 1)} · "
                    f"{format_number(entry.days_to_expiry, 0)} gg. "
                    "Anche le gambe aggiunte ora usano questi valori."
                ).classes(
                    "text-[11px] leading-relaxed mt-1 px-2 py-1 rounded "
                    "bg-[rgba(240,165,0,0.08)] text-[#d9c08a]"
                )
            ui.button("Rifissa i premi ai prezzi correnti", on_click=reprice).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")


# ---------------------------------------------------------------------------
# Costruttore di gambe
# ---------------------------------------------------------------------------


def legs_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def after(action: Any) -> None:
        action()
        ctx.rerender()

    with ui.card().classes(CARD):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Gambe della posizione").classes(TITLE)
            ui.button("+ Aggiungi gamba", on_click=lambda: after(state.add_leg)).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

        with ui.row().classes("w-full gap-2 no-wrap text-[11px] text-[#6b7280] px-1"):
            ui.label("Tipo").classes("w-24")
            ui.label("Posizione").classes("w-24")
            ui.label("Strike").classes("w-24")
            ui.label("Q.tà").classes("w-20")
            ui.label("Premio").classes("w-24")
            ui.label("").classes("w-16")

        for leg in state.legs:
            is_stock = isinstance(leg, StockLeg)
            leg_id = leg.leg_id
            code = moneyness(leg, state.market.spot)
            with ui.row().classes("w-full gap-2 no-wrap items-center"):
                ui.select(
                    {"call": "Call", "put": "Put", "stock": "Azione"},
                    value="stock" if is_stock else leg.right,  # type: ignore[union-attr]
                    on_change=lambda e, i=leg_id: after(lambda: state.set_leg_type(i, e.value)),
                ).classes("w-24").props("dense outlined")
                ui.select(
                    {"long": "Long", "short": "Short"},
                    value=leg.side,
                    on_change=lambda e, i=leg_id: after(lambda: state.set_leg_side(i, e.value)),
                ).classes("w-24").props("dense outlined")
                ui.number(
                    value=leg.entry_price if is_stock else leg.strike,  # type: ignore[union-attr]
                    step=0.5,
                    format="%.2f",
                    on_change=lambda e, i=leg_id: after(lambda: state.set_leg_strike(i, e.value)),
                ).classes("w-24").props("dense outlined").tooltip(
                    "Prezzo di carico dell'azione" if is_stock else "Strike"
                )
                ui.number(
                    value=leg.qty,
                    step=1,
                    min=1,
                    format="%.0f",
                    on_change=lambda e, i=leg_id: after(lambda: state.set_leg_qty(i, e.value)),
                ).classes("w-20").props("dense outlined")

                premium = a.entry_premiums.get(leg_id, 0.0)
                if is_stock:
                    ui.number(value=premium, format="%.2f").classes("w-24").props(
                        "dense outlined readonly"
                    ).tooltip("Per l'azione il costo è il prezzo di carico")
                else:
                    ui.number(
                        value=round(premium, 2),
                        step=0.05,
                        format="%.2f",
                        on_change=lambda e, i=leg_id: after(
                            lambda: state.set_leg_premium(i, e.value)
                        ),
                    ).classes("w-24").props("dense outlined").tooltip(
                        "Premio teorico. Modificalo per imporre un valore manuale."
                    )

                with ui.row().classes("w-16 gap-1 items-center no-wrap"):
                    ui.label(code).classes("text-[10px] font-bold px-1 rounded border").style(
                        f"color: {MONEYNESS_COLOR[code]}; border-color: {MONEYNESS_COLOR[code]}"
                    )
                    ui.button(
                        icon="close",
                        on_click=lambda _, i=leg_id: after(lambda: state.remove_leg(i)),
                    ).props("flat dense round size=sm color=negative")

        with ui.row().classes("w-full items-center justify-between mt-2"):
            if state.has_manual_premiums():
                ui.button(
                    "↺ Riporta tutti i premi al teorico",
                    on_click=lambda: after(state.reset_premiums),
                ).props("flat dense no-caps color=primary").classes("text-xs")
            else:
                ui.label("").classes("grow")
            debit = a.net_cost >= 0
            title = "Costo netto (debito)" if debit else "Credito netto incassato"
            ui.label(f"{title}: {format_signed_money(-a.net_cost, state.currency)}").classes(
                "text-xs"
            ).style(f"color: {COLOR_LOSS if debit else COLOR_PROFIT}")


# ---------------------------------------------------------------------------
# Riepilogo
# ---------------------------------------------------------------------------


def summary_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics
    with ui.card().classes(CARD):
        ui.label(f"{state.ticker} · {state.name} — riepilogo posizione").classes(TITLE)
        with ui.row().classes("w-full gap-2 flex-wrap"):
            debit = a.net_cost >= 0
            stat(
                "Costo / credito netto",
                format_signed_money(-a.net_cost, state.currency),
                tone="loss" if debit else "profit",
                sub="esborso iniziale" if debit else "premio incassato",
            )
            stat(
                "Profitto massimo",
                format_signed_money(a.max_profit, state.currency),
                tone="profit",
                sub="illimitato verso l'alto" if a.profit_unbounded else "a scadenza",
            )
            stat(
                "Perdita massima",
                format_signed_money(a.max_loss, state.currency),
                tone="loss",
                sub="ILLIMITATA — rischio non coperto" if a.loss_unbounded else "a scadenza",
            )
            be_text = (
                "  ·  ".join(format_number(b, 2) for b in a.break_evens)
                if a.break_evens
                else "nessuno"
            )
            stat("Break-even", be_text, tone="profit")

        if a.loss_unbounded:
            ui.label(
                "⚠ Questa posizione ha perdita potenzialmente illimitata: una gamba "
                "venduta non è coperta da una comprata più esterna."
            ).classes("text-xs mt-2 px-3 py-2 rounded bg-[#2a1216]").style(f"color: {COLOR_LOSS}")


# ---------------------------------------------------------------------------
# Greche
# ---------------------------------------------------------------------------


def greeks_panel(ctx: PageContext) -> None:
    g = ctx.analytics.greeks
    with ui.card().classes(CARD):
        ui.label("Greche aggregate della posizione").classes(TITLE)
        ui.label("Somma delle greche di tutte le gambe, con segno e quantità.").classes(FAINT)
        for symbol, name, attribute, unit, description in GREEK_ROWS:
            value = getattr(g, attribute)
            with ui.column().classes("w-full gap-0 border-t border-[#1e222d] py-2"):
                with ui.row().classes("w-full items-baseline gap-3 no-wrap"):
                    ui.label(symbol).classes("text-lg font-bold w-6").style("color: #b07dff")
                    ui.label(name).classes("text-sm font-semibold grow")
                    ui.label(f"{format_number(value, 4)} {unit}").classes(
                        "text-sm font-bold"
                    ).style(f"color: {COLOR_PROFIT if value >= 0 else COLOR_LOSS}")
                ui.label(description).classes(FAINT)


# ---------------------------------------------------------------------------
# Vol crush
# ---------------------------------------------------------------------------


def vol_crush_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_iv_sim(value: float) -> None:
        state.iv_sim = value / 100
        ctx.rerender()

    with ui.card().classes(CARD):
        ui.label("Simulatore di vol crush (IV indipendente)").classes(TITLE)
        ui.label(
            "Sposta solo la volatilità implicita tenendo fermo tutto il resto: spot, "
            "giorni, tasso. È l'effetto isolato della vega. Un calo netto di IV dopo "
            "un evento, tipicamente gli earnings, è il classico vol crush."
        ).classes(FAINT)
        ui.label(f"IV simulata: {format_percent(state.iv_sim, 1)}").classes(MUTED + " mt-2")
        throttled_slider(
            minimum=1,
            maximum=150,
            step=1,
            value=state.iv_sim * 100,
            on_value=set_iv_sim,
        ).classes("w-full")
        with ui.row().classes("w-full gap-2 flex-wrap mt-1"):
            stat(
                f"Valore oggi @ IV {format_percent(state.market.iv, 0)}",
                format_signed_money(a.value_now_current_iv, state.currency),
            )
            stat(
                f"Valore oggi @ IV {format_percent(state.iv_sim, 0)}",
                format_signed_money(a.value_now_sim_iv, state.currency),
            )
            iv_delta = format_number((state.iv_sim - state.market.iv) * 100, 1)
            stat(
                "Effetto vega",
                format_signed_money(a.vol_crush_effect, state.currency),
                tone="profit" if a.vol_crush_effect >= 0 else "loss",
                sub=f"per ΔIV di {iv_delta} punti",
            )


# ---------------------------------------------------------------------------
# Scenario a scadenza
# ---------------------------------------------------------------------------


def scenario_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_target(value: Any) -> None:
        if value is None:
            return
        state.target = float(value)
        ctx.rerender()

    with ui.card().classes(CARD):
        ui.label("Scenario a scadenza").classes(TITLE)
        ui.label(
            "Inserisci un prezzo-target del sottostante a scadenza e ottieni il P&L "
            "esatto su tutte le gambe."
        ).classes(FAINT)
        ui.number(
            "Prezzo-target",
            value=state.target,
            step=0.5,
            format="%.2f",
            on_change=lambda e: set_target(e.value),
        ).classes("w-full mt-2").props("dense outlined suffix=$")
        throttled_slider(
            minimum=round(a.chart_low, 1),
            maximum=round(a.chart_high, 1),
            step=0.5,
            value=min(max(state.target, a.chart_low), a.chart_high),
            on_value=set_target,
        ).classes("w-full")

        with ui.row().classes("w-full gap-2 mt-1"):
            stat(
                f"P&L a scadenza @ {format_money(state.target, state.currency)}",
                format_signed_money(a.scenario_pl, state.currency),
                tone="profit" if a.scenario_pl >= 0 else "loss",
                sub="in profitto" if a.scenario_pl >= 0 else "in perdita",
            )

        with ui.row().classes("w-full gap-2 no-wrap text-[11px] text-[#6b7280] mt-3 px-1"):
            ui.label("Gamba").classes("grow")
            ui.label("Payoff").classes("w-24 text-right")
            ui.label("Premio").classes("w-24 text-right")
            ui.label("P&L gamba").classes("w-28 text-right")

        for leg in state.legs:
            premium = a.entry_premiums.get(leg.leg_id, 0.0)
            if isinstance(leg, StockLeg):
                payoff = state.target
                label = (
                    f"{leg.side.title()} {format_number(leg.qty, 0)}× Azione @ "
                    f"{format_number(leg.entry_price, 0)}"
                )
            else:
                payoff = (
                    max(state.target - leg.strike, 0.0)
                    if leg.right == "call"
                    else max(leg.strike - state.target, 0.0)
                )
                label = (
                    f"{leg.side.title()} {format_number(leg.qty, 0)}× "
                    f"{leg.right.title()} {format_number(leg.strike, 0)}"
                )
            sign = 1.0 if leg.side == "long" else -1.0
            pl = sign * (payoff - premium) * leg.qty
            with ui.row().classes(
                "w-full gap-2 no-wrap text-xs text-[#c9cfdd] py-1 border-t border-[#1e222d]"
            ):
                ui.label(label).classes("grow")
                ui.label(format_money(payoff, state.currency)).classes("w-24 text-right")
                ui.label(format_money(premium, state.currency)).classes("w-24 text-right")
                ui.label(format_signed_money(pl, state.currency)).classes(
                    "w-28 text-right font-semibold"
                ).style(f"color: {COLOR_PROFIT if pl >= 0 else COLOR_LOSS}")


# ---------------------------------------------------------------------------
# Costo dell'operazione
# ---------------------------------------------------------------------------


def cost_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_sizing(*, packages: Any = None, contract_multiplier: Any = None) -> None:
        # Parametri espliciti invece di **kwargs: mypy può verificare i tipi
        # solo se sa quali chiavi arriveranno.
        sizing = state.sizing
        if packages:
            sizing = replace(sizing, packages=max(1, int(packages)))
        if contract_multiplier:
            sizing = replace(sizing, contract_multiplier=max(1.0, float(contract_multiplier)))
        if sizing == state.sizing:
            return
        state.sizing = sizing
        ctx.rerender()

    with ui.card().classes(CARD):
        ui.label("Costo dell'operazione").classes(TITLE)
        ui.label(
            "Traduce i prezzi teorici in esborso reale. Ogni contratto controlla "
            f"{format_number(state.sizing.contract_multiplier, 0)} unità di sottostante: "
            "il costo di una gamba è premio × moltiplicatore × contratti × pacchetti."
        ).classes(FAINT)

        with ui.row().classes("w-full gap-2 no-wrap mt-2"):
            ui.number(
                "Pacchetti (repliche)",
                value=state.sizing.packages,
                step=1,
                min=1,
                format="%.0f",
                on_change=lambda e: set_sizing(packages=e.value),
            ).classes("grow").props("dense outlined")
            ui.number(
                "Moltiplicatore contratto",
                value=state.sizing.contract_multiplier,
                step=1,
                min=1,
                format="%.0f",
                on_change=lambda e: set_sizing(contract_multiplier=e.value),
            ).classes("grow").props("dense outlined suffix=az.")

        with ui.row().classes("w-full gap-2 no-wrap text-[11px] text-[#6b7280] mt-3 px-1"):
            ui.label("Gamba").classes("grow")
            ui.label("Prezzo unit.").classes("w-24 text-right")
            ui.label("Unità tot.").classes("w-24 text-right")
            ui.label("Flusso").classes("w-28 text-right")

        for leg_cost in a.cost.legs:
            leg = leg_cost.resolved.leg
            short = leg.side == "short"
            if isinstance(leg, StockLeg):
                label = f"{leg.side.title()} Azione @ {format_number(leg.entry_price, 0)}"
            else:
                label = f"{leg.side.title()} {leg.right.title()} {format_number(leg.strike, 0)}"
            with ui.row().classes(
                "w-full gap-2 no-wrap text-xs text-[#c9cfdd] py-1 border-t border-[#1e222d]"
            ):
                ui.label(f"{label} ×{format_number(leg.qty, 0)}").classes("grow")
                ui.label(format_money(leg_cost.unit_price, state.currency)).classes(
                    "w-24 text-right"
                )
                ui.label(format_number(leg_cost.units, 0)).classes("w-24 text-right")
                ui.label(
                    format_signed_money(
                        leg_cost.gross if short else -leg_cost.gross, state.currency
                    )
                ).classes("w-28 text-right font-semibold").style(
                    f"color: {COLOR_PROFIT if short else COLOR_LOSS}"
                )

        with ui.row().classes("w-full gap-2 flex-wrap mt-3"):
            stat(
                "Esborso (premi/azioni pagati)",
                format_signed_money(-a.cost.total_outflow, state.currency),
                tone="loss",
            )
            stat(
                "Incasso (premi venduti)",
                format_signed_money(a.cost.total_inflow, state.currency),
                tone="profit",
            )
            debit = a.cost.net >= 0
            packages = state.sizing.packages
            stat(
                "Costo netto totale" if debit else "Credito netto totale",
                format_signed_money(-a.cost.net, state.currency),
                tone="loss" if debit else "profit",
                sub=f"per {packages} pacchett{'o' if packages == 1 else 'i'}",
            )

        if a.cost.net < 0:
            ui.label(
                "Le posizioni a credito richiedono in genere un margine presso il "
                "broker, non mostrato qui."
            ).classes(FAINT)
