"""Pannello «Riepilogo della posizione»: i numeri chiave."""

from __future__ import annotations

from nicegui import ui

from ..context import PageContext
from ..formatting import (
    format_expiry,
    format_number,
    format_percent,
    format_signed_money,
)
from ..widgets import (
    CARD,
    DANGER_STRIP,
    card_title,
    stat,
)


def summary_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics
    with ui.card().classes(CARD):
        card_title(
            "Riepilogo della posizione",
            "insights",
            subtitle=f"{state.ticker} · {state.name} · "
            f"scade {format_expiry(state.market.days_to_expiry)}",
        )
        with ui.element("div").classes(
            "w-full grid gap-2 grid-cols-2 md:grid-cols-3 2xl:grid-cols-5"
        ):
            debit = a.net_cost >= 0
            stat(
                "Costo / credito netto",
                format_signed_money(-a.net_cost, state.currency),
                tone="loss" if debit else "profit",
                sub="esborso iniziale" if debit else "premio incassato",
                icon="account_balance_wallet",
            )
            stat(
                "Profitto massimo",
                format_signed_money(a.max_profit, state.currency),
                tone="profit",
                sub="illimitato verso l'alto" if a.profit_unbounded else "a scadenza",
                icon="trending_up",
            )
            stat(
                "Perdita massima",
                format_signed_money(a.max_loss, state.currency),
                tone="loss",
                sub="ILLIMITATA — rischio non coperto" if a.loss_unbounded else "a scadenza",
                icon="trending_down",
            )
            be_text = (
                "  ·  ".join(format_number(b, 2) for b in a.break_evens)
                if a.break_evens
                else "nessuno"
            )
            stat("Break-even", be_text, icon="adjust")
            stat(
                "Probabilità di profitto",
                format_percent(a.prob_profit, 1),
                tone="profit" if a.prob_profit >= 0.5 else "loss",
                sub="a scadenza, secondo il modello",
                icon="casino",
            )

        if a.loss_unbounded:
            with ui.row().classes(DANGER_STRIP + " mt-3"):
                ui.icon("warning", size="18px")
                ui.label(
                    "Questa posizione ha perdita potenzialmente illimitata: una gamba "
                    "venduta non è coperta da una comprata più esterna."
                ).classes("grow")
