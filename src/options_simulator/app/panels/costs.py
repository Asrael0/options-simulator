"""«Cost of the trade» panel: from theoretical prices to the real outlay."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from nicegui import ui

from ...pricing import StockLeg
from ..context import PageContext
from ..formatting import (
    format_money,
    format_number,
    format_signed_money,
)
from ..i18n import tr, trn
from ..widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    card_title,
    commit_on_leave,
    stat,
)


def cost_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_sizing(*, packages: Any = None, contract_multiplier: Any = None) -> None:
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
        card_title(tr("Costo dell'operazione"), "receipt_long")
        ui.label(
            tr(
                "Traduce i prezzi teorici in esborso reale. Ogni contratto controlla "
                "{contract_multiplier} unità di sottostante: il costo di una gamba è "
                "premio × moltiplicatore × contratti × pacchetti.",
                contract_multiplier=format_number(state.sizing.contract_multiplier, 0),
            )
        ).classes(FAINT)

        with ui.row().classes("w-full gap-2 no-wrap mt-2"):
            commit_on_leave(
                ui.number(
                    tr("Pacchetti (repliche)"),
                    value=state.sizing.packages,
                    step=1,
                    min=1,
                    format="%.0f",
                )
                .classes("grow")
                .props("dense outlined"),
                lambda v: set_sizing(packages=v),
            )
            commit_on_leave(
                ui.number(
                    tr("Moltiplicatore contratto"),
                    value=state.sizing.contract_multiplier,
                    step=1,
                    min=1,
                    format="%.0f",
                )
                .classes("grow")
                .props(f"dense outlined suffix={tr('az.')}"),
                lambda v: set_sizing(contract_multiplier=v),
            )

        with ui.row().classes("w-full gap-2 no-wrap sim-thead mt-4 px-1"):
            ui.label(tr("Gamba")).classes("grow")
            ui.label(tr("Prezzo unit.")).classes("w-24 text-right")
            ui.label(tr("Unità tot.")).classes("w-24 text-right")
            ui.label(tr("Flusso")).classes("w-28 text-right")

        for leg_cost in a.cost.legs:
            leg = leg_cost.resolved.leg
            short = leg.side == "short"
            if isinstance(leg, StockLeg):
                label = tr(
                    "{side} azione @ {price}",
                    side=tr(leg.side.title()),
                    price=format_number(leg.entry_price, 0),
                )
            else:
                label = (
                    f"{tr(leg.side.title())} {tr(leg.right.title())} {format_number(leg.strike, 0)}"
                )
            with ui.row().classes("w-full gap-2 no-wrap text-xs t-text2 t-num py-2 sim-divider"):
                ui.label(tr("{label} ×{qty}", label=label, qty=format_number(leg.qty, 0))).classes(
                    "grow"
                )
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
                tr("Esborso (premi/azioni pagati)"),
                format_signed_money(-a.cost.total_outflow, state.currency),
                tone="loss",
            )
            stat(
                tr("Incasso (premi venduti)"),
                format_signed_money(a.cost.total_inflow, state.currency),
                tone="profit",
            )
            debit = a.cost.net >= 0
            packages = state.sizing.packages
            stat(
                tr("Costo netto totale") if debit else tr("Credito netto totale"),
                format_signed_money(-a.cost.net, state.currency),
                tone="loss" if debit else "profit",
                sub=trn("per {n} pacchetto", "per {n} pacchetti", packages),
            )

        if a.cost.net < 0:
            ui.label(
                tr(
                    "Le posizioni a credito richiedono in genere un margine presso il "
                    "broker, non mostrato qui."
                )
            ).classes(FAINT)
