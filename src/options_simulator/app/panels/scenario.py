"""Scenario simulator: price, date and IV, with the P&L breakdown."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from nicegui import ui

from ...pricing import StockLeg
from ..context import PageContext
from ..formatting import (
    format_date,
    format_money,
    format_number,
    format_percent,
    format_signed_money,
)
from ..i18n import tr
from ..state import MATRIX_IV_MOVES, MATRIX_PRICE_MOVES, PositionState, Scenario
from ..widgets import (
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    card_title,
    stat,
    throttled_slider,
)

# Labels are in Italian and go through tr() in _chips.
PRICE_CHIPS = [("−10%", -0.10), ("−5%", -0.05), ("Oggi", 0.0), ("+5%", 0.05), ("+10%", 0.10)]
IV_CHIPS = [("Crollo −50%", -0.50), ("−30%", -0.30), ("Attuale", 0.0), ("+30%", 0.30)]


def _leg_label(leg: Any) -> str:
    if isinstance(leg, StockLeg):
        return tr("{side} {qty}× azione", side=tr(leg.side.title()), qty=format_number(leg.qty, 0))
    return (
        f"{tr(leg.side.title())} {format_number(leg.qty, 0)}× {tr(leg.right)} "
        f"{format_number(leg.strike, 2)}"
    )


def _chips(options: list[tuple[str, Any]], on_pick: Any, active: Any) -> None:
    with ui.row().classes("gap-1 flex-wrap"):
        for label, value in options:
            selected = active is not None and abs(value - active) < 1e-9
            ui.button(tr(label), on_click=lambda _, v=value: on_pick(v)).props(
                "dense no-caps unelevated color=primary" if selected else "dense no-caps outline"
            ).classes("text-[11px] px-2" + ("" if selected else " t-muted"))


def scenario_panel(ctx: PageContext) -> None:
    """What happens if in N days the stock is at X and IV is Y."""
    state = ctx.state
    a = ctx.analytics
    sc = a.scenario
    m = state.market
    dte = m.days_to_expiry
    cur = state.currency

    def set_price(value: Any) -> None:
        if value:
            state.target = float(value)
            ctx.rerender()

    def set_days(value: float) -> None:
        state.days_forward = min(max(float(value), 0.0), dte)
        ctx.rerender()

    def set_iv(value: float) -> None:
        state.iv_sim = max(float(value), 0.01)
        ctx.rerender()

    def reset() -> None:
        state.target, state.days_forward, state.iv_sim = m.spot, 0.0, m.iv
        ctx.rerender()

    card_title(
        tr("Simulatore di scenari"),
        "science",
        subtitle=tr(
            "Scegli dove sarà il titolo, fra quanti giorni e con quale volatilità: "
            "vedi il P&L e da dove viene."
        ),
    )

    with ui.row().classes("w-full gap-8 no-wrap max-lg:flex-wrap items-start"):
        # --- Controls -------------------------------------------------------
        with ui.column().classes("grow basis-0 min-w-[280px] gap-4"):
            with ui.column().classes("w-full gap-1"):
                move = sc.price / m.spot - 1
                ui.label(
                    tr(
                        "Prezzo del titolo: {price} ({x}{move} da oggi)",
                        price=format_money(sc.price, cur),
                        x="+" if move >= 0 else "",
                        move=format_percent(move, 1),
                    )
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=round(a.chart_low, 1),
                    maximum=round(a.chart_high, 1),
                    step=0.5,
                    value=min(max(sc.price, a.chart_low), a.chart_high),
                    on_value=set_price,
                ).classes("w-full")
                _chips(
                    [(label, round(m.spot * (1 + d), 2)) for label, d in PRICE_CHIPS],
                    set_price,
                    round(sc.price, 2),
                )

            with ui.column().classes("w-full gap-1"):
                when = date.today() + timedelta(days=round(sc.days))
                ui.label(
                    tr("Quando: oggi")
                    if sc.days <= 0
                    else tr(
                        "Quando: fra {days} gg ({strftime})",
                        days=format_number(sc.days, 0),
                        strftime=format_date(when),
                    )
                    + (tr(" · a scadenza") if sc.days >= dte else "")
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=0, maximum=max(dte, 1), step=1, value=sc.days, on_value=set_days
                ).classes("w-full")
                _chips(
                    [
                        ("Oggi", 0.0),
                        ("1 settimana", min(7.0, dte)),
                        ("Metà", round(dte / 2)),
                        ("Scadenza", dte),
                    ],
                    set_days,
                    sc.days,
                )

            with ui.column().classes("w-full gap-1"):
                change = sc.iv / m.iv - 1 if m.iv > 0 else 0.0
                ui.label(
                    tr("Volatilità implicita: {iv}", iv=format_percent(sc.iv, 1))
                    + (
                        tr(
                            " ({x}{change} rispetto a oggi)",
                            x="+" if change >= 0 else "",
                            change=format_percent(change, 0),
                        )
                        if abs(change) > 1e-9
                        else tr(" (come oggi)")
                    )
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=1,
                    maximum=150,
                    step=1,
                    value=round(sc.iv * 100),
                    on_value=lambda v: set_iv(v / 100),
                ).classes("w-full")
                _chips(
                    [(label, round(m.iv * (1 + d), 6)) for label, d in IV_CHIPS],
                    set_iv,
                    round(sc.iv, 6),
                )
                ui.label(
                    tr(
                        "Il «vol crush» è il crollo della IV dopo un evento atteso, tipicamente "
                        "gli utili trimestrali: chi ha comprato opzioni perde anche se il prezzo "
                        "si muove nella direzione giusta."
                    )
                ).classes(FAINT)

            ui.button(tr("Azzera scenario"), icon="restart_alt", on_click=reset).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs self-start")

        # --- Result -------------------------------------------------------
        with ui.column().classes("grow basis-0 min-w-[300px] gap-3"):
            sizing = state.sizing
            units = sizing.contract_multiplier * sizing.packages
            stat(
                tr("P&L nello scenario"),
                format_signed_money(sc.pl, cur),
                tone="profit" if sc.pl >= 0 else "loss",
                sub=tr(
                    "per azione · {signed_money} sulla posizione reale ({units} azioni)",
                    signed_money=format_signed_money(sc.pl * units, cur),
                    units=format_number(units, 0),
                ),
                icon="flag",
            )

            ui.label(tr("Da dove viene")).classes("sim-stat-label mt-1")
            parts = [
                ("Se chiudessi oggi", sc.pl_today, "today"),
                ("Movimento del prezzo", sc.effect_price, "show_chart"),
                ("Tempo che passa (theta)", sc.effect_time, "hourglass_bottom"),
                ("Cambio di volatilità (vega)", sc.effect_vol, "waves"),
            ]
            largest = max((abs(v) for _, v, _ in parts), default=1.0) or 1.0
            with ui.column().classes("w-full gap-1"):
                for label, value, icon in parts:
                    color = COLOR_PROFIT if value >= 0 else COLOR_LOSS
                    with ui.row().classes("w-full items-center gap-2 no-wrap"):
                        ui.icon(icon, size="16px").classes("t-muted")
                        ui.label(tr(label)).classes("text-xs t-text2 w-[170px] shrink-0")
                        with (
                            ui.element("div")
                            .classes("grow h-2 rounded-full")
                            .style("background: var(--surface-2)")
                        ):
                            ui.element("div").classes("h-2 rounded-full").style(
                                f"width: {abs(value) / largest * 100:.1f}%; background: {color}"
                            )
                        ui.label(format_signed_money(value, cur)).classes(
                            "text-xs font-semibold t-num w-[78px] text-right"
                        ).style(f"color: {color}")
                with ui.row().classes("w-full items-center gap-2 no-wrap sim-divider pt-1"):
                    ui.label(tr("= P&L nello scenario")).classes(
                        "text-xs font-semibold t-text grow"
                    )
                    ui.label(format_signed_money(sc.pl, cur)).classes(
                        "text-xs font-semibold t-num w-[78px] text-right"
                    ).style(f"color: {COLOR_PROFIT if sc.pl >= 0 else COLOR_LOSS}")

            with ui.row().classes("w-full gap-2 no-wrap sim-thead mt-2 px-1"):
                ui.label(tr("Gamba")).classes("grow")
                ui.label(tr("Pagato")).classes("w-20 text-right")
                ui.label(tr("Varrà")).classes("w-20 text-right")
                ui.label(tr("P&L")).classes("w-24 text-right")
            legs = {leg.leg_id: leg for leg in state.legs}
            for row in sc.legs:
                with ui.row().classes(
                    "w-full gap-2 no-wrap text-xs t-text2 t-num py-1.5 sim-divider px-1"
                ):
                    ui.label(_leg_label(legs[row.leg_id])).classes("grow")
                    ui.label(format_number(row.entry, 2)).classes("w-20 text-right")
                    ui.label(format_number(row.value, 2)).classes("w-20 text-right")
                    ui.label(format_signed_money(row.pl, cur)).classes(
                        "w-24 text-right font-semibold"
                    ).style(f"color: {COLOR_PROFIT if row.pl >= 0 else COLOR_LOSS}")

    _scenario_matrix(state, sc)


def _scenario_matrix(state: PositionState, sc: Scenario) -> None:
    m = state.market
    cur = state.currency
    largest = max((abs(v) for row in sc.matrix for v in row), default=1.0) or 1.0
    when = "oggi" if sc.days <= 0 else f"fra {format_number(sc.days, 0)} gg"
    ui.label(tr("Matrice degli scenari · P&L {when}", when=when)).classes("sim-card-title mt-6")
    ui.label(
        tr(
            "Ogni casella combina una variazione del prezzo (colonne) e della IV (righe). "
            "Utile per vedere a colpo d'occhio se la posizione teme di più il prezzo o la "
            "volatilità."
        )
    ).classes(FAINT)
    with ui.column().classes("w-full gap-1 overflow-x-auto mt-2"):
        with ui.row().classes("min-w-[620px] w-full no-wrap gap-1"):
            ui.label(tr("IV \\ prezzo")).classes("w-[96px] sim-thead self-end")
            for move in MATRIX_PRICE_MOVES:
                with ui.column().classes("grow basis-0 gap-0 items-center"):
                    ui.label(
                        tr("oggi")
                        if move == 0
                        else tr(
                            "{x}{move}", x="+" if move > 0 else "", move=format_percent(move, 1)
                        )
                    ).classes("sim-thead")
                    ui.label(format_number(m.spot * (1 + move), 2)).classes("text-[11px] t-faint")
        for iv_move, row in zip(MATRIX_IV_MOVES, sc.matrix, strict=True):
            with ui.row().classes("min-w-[620px] w-full no-wrap gap-1"):
                with ui.column().classes("w-[96px] gap-0 justify-center"):
                    ui.label(
                        tr("IV attuale")
                        if iv_move == 0
                        else tr(
                            "IV {x}{iv_move}",
                            x="+" if iv_move > 0 else "",
                            iv_move=format_percent(iv_move, 0),
                        )
                    ).classes("text-xs t-text2")
                    ui.label(format_percent(m.iv * (1 + iv_move), 1)).classes("text-[11px] t-faint")
                for move, value in zip(MATRIX_PRICE_MOVES, row, strict=True):
                    strength = 12 + 58 * min(abs(value) / largest, 1.0)
                    color = "var(--profit)" if value >= 0 else "var(--loss)"
                    centre = move == 0 and iv_move == 0
                    ui.label(format_signed_money(value, cur)).classes(
                        "grow basis-0 text-center text-xs font-semibold t-num py-2 "
                        "rounded-md t-text" + (" ring-2 ring-[var(--accent)]" if centre else "")
                    ).style(f"background: color-mix(in srgb, {color} {strength:.0f}%, transparent)")
