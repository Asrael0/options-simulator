"""«Position summary» panel: the key figures."""

from __future__ import annotations

from nicegui import ui

from ..context import PageContext
from ..formatting import (
    format_expiry,
    format_number,
    format_percent,
    format_signed_money,
)
from ..i18n import tr
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
            tr("Riepilogo della posizione"),
            "insights",
            subtitle=tr(
                "{ticker} · {name} · scade {expiry}",
                ticker=state.ticker,
                name=state.name,
                expiry=format_expiry(state.market.days_to_expiry),
            ),
        )
        with ui.element("div").classes(
            "w-full grid gap-2 grid-cols-2 md:grid-cols-3 2xl:grid-cols-5"
        ):
            debit = a.net_cost >= 0
            stat(
                tr("Costo / credito netto"),
                format_signed_money(-a.net_cost, state.currency),
                tone="loss" if debit else "profit",
                sub=tr("esborso iniziale") if debit else tr("premio incassato"),
                icon="account_balance_wallet",
            )
            stat(
                tr("Profitto massimo"),
                format_signed_money(a.max_profit, state.currency),
                tone="profit",
                sub=tr("illimitato verso l'alto") if a.profit_unbounded else tr("a scadenza"),
                icon="trending_up",
            )
            stat(
                tr("Perdita massima"),
                format_signed_money(a.max_loss, state.currency),
                tone="loss",
                sub=tr("ILLIMITATA — rischio non coperto")
                if a.loss_unbounded
                else tr("a scadenza"),
                icon="trending_down",
            )
            be_text = (
                "  ·  ".join(format_number(b, 2) for b in a.break_evens)
                if a.break_evens
                else "nessuno"
            )
            stat(tr("Break-even"), be_text, icon="adjust")
            stat(
                tr("Probabilità di profitto"),
                format_percent(a.prob_profit, 1),
                tone="profit" if a.prob_profit >= 0.5 else "loss",
                sub=tr("a scadenza, secondo il modello"),
                icon="casino",
            )

        if a.loss_unbounded:
            with ui.row().classes(DANGER_STRIP + " mt-3"):
                ui.icon("warning", size="18px")
                ui.label(
                    tr(
                        "Questa posizione ha perdita potenzialmente illimitata: una gamba "
                        "venduta non è coperta da una comprata più esterna."
                    )
                ).classes("grow")
