"""«Chain» tab: calls on the left, puts on the right, strikes in the middle."""

from __future__ import annotations

from datetime import date
from typing import Any

from nicegui import ui

from ...formatting import format_number, format_percent
from ...i18n import tr
from ...market_data import (
    Chain,
    Quote,
)
from ...widgets import (
    FAINT,
)
from .view import SIDE_CELLS, MarketView, price_text


def _side_cells(quote: Quote | None, *, mirrored: bool) -> None:
    values = (
        ["—"] * 5
        if quote is None
        else [
            price_text(quote.bid),
            price_text(quote.ask),
            format_percent(quote.iv, 1) if quote.iv else "—",
            format_number(quote.delta, 2) if quote.delta is not None else "—",
            format_number(quote.open_interest, 0),
        ]
    )
    if mirrored:
        values = values[::-1]
    for value in values:
        ui.label(value).classes("w-[62px] text-right")


def render_chain(view: MarketView, chain: Chain, expiry: date, on_pick: Any) -> None:
    strikes = view.visible_strikes()
    spot = chain.spot
    with ui.column().classes("w-full gap-0 overflow-x-auto"):
        with ui.row().classes("min-w-[760px] w-full no-wrap gap-0 pb-1"):
            ui.label(tr("CALL")).classes("grow basis-0 text-center sim-eyebrow")
            ui.label("").classes("w-[90px]")
            ui.label(tr("PUT")).classes("grow basis-0 text-center sim-eyebrow")
        with ui.row().classes("min-w-[760px] w-full no-wrap gap-0 sim-thead pb-2"):
            with ui.row().classes("grow basis-0 no-wrap gap-1 justify-end pr-2"):
                for name in SIDE_CELLS[::-1]:
                    ui.label(tr(name)).classes("w-[62px] text-right")
            ui.label(tr("Strike")).classes("w-[90px] text-center")
            with ui.row().classes("grow basis-0 no-wrap gap-1 pl-2"):
                for name in SIDE_CELLS:
                    ui.label(tr(name)).classes("w-[62px] text-right")

        spot_drawn = False
        for strike in strikes:
            if not spot_drawn and strike >= spot:
                spot_drawn = True
                with ui.row().classes("min-w-[760px] w-full items-center gap-2 no-wrap py-0.5"):
                    ui.element("div").classes("grow h-px").style("background: var(--info)")
                    ui.label(tr("prezzo {spot}", spot=format_number(spot, 2))).classes(
                        "text-[11px] font-semibold"
                    ).style("color: var(--info)")
                    ui.element("div").classes("grow h-px").style("background: var(--info)")
            call = chain.quote(expiry, "call", strike)
            put = chain.quote(expiry, "put", strike)
            with ui.row().classes(
                "min-w-[760px] w-full no-wrap gap-0 text-[13px] t-text2 t-num sim-divider"
            ):
                with (
                    ui.row()
                    .classes(
                        "grow basis-0 no-wrap gap-1 justify-end pr-2 py-1.5 cursor-pointer "
                        "sim-chain-cell" + (" sim-itm" if strike < spot else "")
                    )
                    .on("click", lambda _, k=strike: on_pick("call", k))
                ):
                    _side_cells(call, mirrored=True)
                ui.label(format_number(strike, 2)).classes(
                    "w-[90px] text-center font-semibold t-text py-1.5"
                )
                with (
                    ui.row()
                    .classes(
                        "grow basis-0 no-wrap gap-1 pl-2 py-1.5 cursor-pointer sim-chain-cell"
                        + (" sim-itm" if strike > spot else "")
                    )
                    .on("click", lambda _, k=strike: on_pick("put", k))
                ):
                    _side_cells(put, mirrored=False)
    ui.label(
        tr(
            "Le righe colorate sono in the money. Clicca il lato call o put di una riga "
            "per comprare o vendere quell'opzione."
        )
    ).classes(FAINT + " mt-2")
