"""Pannello «Gambe della posizione»: il costruttore riga per riga."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ...pricing import StockLeg, moneyness
from ..context import PageContext
from ..formatting import (
    format_signed_money,
)
from ..widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    MONEYNESS_COLOR,
    card_title,
    commit_on_leave,
)


def legs_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def after(action: Any) -> None:
        action()
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title(
            "Gambe della posizione",
            "stacked_line_chart",
            subtitle="Ogni riga è un contratto o un'azione",
            action=("Aggiungi gamba", "add", lambda: after(state.add_leg)),
        )

        # Su schermi stretti la tabella scorre in orizzontale dentro la card,
        # invece di schiacciare i campi o allargare la pagina.
        with ui.column().classes("w-full gap-2 overflow-x-auto pb-1"):
            with ui.row().classes("min-w-[600px] gap-2 no-wrap sim-thead px-1"):
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
                with ui.row().classes("min-w-[600px] gap-2 no-wrap items-center"):
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
                    commit_on_leave(
                        ui.number(
                            value=leg.entry_price if is_stock else leg.strike,  # type: ignore[union-attr]
                            step=0.5,
                            format="%.2f",
                        )
                        .classes("w-24")
                        .props("dense outlined")
                        .tooltip("Prezzo di carico dell'azione" if is_stock else "Strike"),
                        lambda v, i=leg_id: after(lambda: state.set_leg_strike(i, v)),
                    )
                    commit_on_leave(
                        ui.number(value=leg.qty, step=1, min=1, format="%.0f")
                        .classes("w-20")
                        .props("dense outlined"),
                        lambda v, i=leg_id: after(lambda: state.set_leg_qty(i, v)),
                    )

                    premium = a.entry_premiums.get(leg_id, 0.0)
                    if is_stock:
                        ui.number(value=premium, format="%.2f").classes("w-24").props(
                            "dense outlined readonly"
                        ).tooltip("Per l'azione il costo è il prezzo di carico")
                    else:
                        commit_on_leave(
                            ui.number(value=round(premium, 2), step=0.05, format="%.2f")
                            .classes("w-24")
                            .props("dense outlined")
                            .tooltip("Premio teorico. Modificalo per imporre un valore manuale."),
                            lambda v, i=leg_id: after(lambda: state.set_leg_premium(i, v)),
                        )

                    with ui.row().classes("w-16 gap-1 items-center no-wrap"):
                        ui.label(code).classes("sim-chip").style(f"color: {MONEYNESS_COLOR[code]}")
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda _, i=leg_id: after(lambda: state.remove_leg(i)),
                        ).props("flat dense round size=sm").classes("t-faint").tooltip(
                            "Rimuovi gamba"
                        )

        with ui.row().classes("w-full items-center justify-between mt-auto pt-2"):
            if state.has_manual_premiums():
                ui.button(
                    "Riporta tutti i premi al teorico",
                    icon="restart_alt",
                    on_click=lambda: after(state.reset_premiums),
                ).props("flat dense no-caps color=primary").classes("text-xs")
            else:
                ui.label("").classes("grow")
            debit = a.net_cost >= 0
            title = "Costo netto (debito)" if debit else "Credito netto incassato"
            ui.label(f"{title}: {format_signed_money(-a.net_cost, state.currency)}").classes(
                "text-sm font-semibold t-num"
            ).style(f"color: {COLOR_LOSS if debit else COLOR_PROFIT}")
