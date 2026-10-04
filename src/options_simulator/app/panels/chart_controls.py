"""Comandi sopra il grafico: tempo che scorre, confronto, esportazione."""

from __future__ import annotations

import base64
from datetime import date, timedelta

from nicegui import ui

from .. import auth, saved
from ..context import PageContext
from ..formatting import (
    format_number,
)
from ..theme import chart_palette
from ..widgets import (
    throttled_slider,
)

NO_COMPARISON = ""


def chart_controls_panel(ctx: PageContext) -> None:
    """Tempo che scorre, confronto con una posizione salvata, esportazione."""
    state = ctx.state
    dte = state.market.days_to_expiry
    forward = min(state.days_forward, dte)
    playing = ctx.animation is not None and ctx.animation.active

    def set_forward(value: float) -> None:
        state.days_forward = value
        ctx.rerender()

    def toggle_play() -> None:
        if ctx.animation is None:
            return
        if ctx.animation.active:
            ctx.animation.deactivate()
        else:
            if state.days_forward >= dte:
                state.days_forward = 0.0
            ctx.animation.activate()
        ctx.rerender()

    def set_comparison(position_id: str) -> None:
        username = auth.current_username()
        item = saved.get(username, position_id) if username and position_id else None
        if item is None:
            state.comparison, state.comparison_name = None, ""
        else:
            try:
                state.comparison = saved.from_dict(item.data)
            except ValueError:
                ui.notify("Questa posizione salvata è danneggiata", type="negative")
                return
            state.comparison_name = item.name
        ctx.rerender()

    async def export_png() -> None:
        if ctx.main_chart is None:
            return
        url = await ctx.main_chart.run_chart_method(
            "getDataURL",
            {"pixelRatio": 2, "backgroundColor": chart_palette()["surface"]},
            timeout=5,
        )
        content = base64.b64decode(str(url).split(",", 1)[1])
        ui.download.content(content, f"{state.ticker or 'payoff'}-grafico.png", "image/png")

    with ui.row().classes("w-full items-center gap-x-5 gap-y-2 px-2 pt-1 flex-wrap"):
        # Tempo
        with ui.row().classes("items-center gap-2 no-wrap grow min-w-[260px]"):
            ui.button(icon="pause" if playing else "play_arrow", on_click=toggle_play).props(
                "unelevated round dense color=primary"
            ).tooltip("Ferma" if playing else "Fai scorrere il tempo fino alla scadenza")
            with ui.column().classes("gap-0 grow"):
                when = date.today() + timedelta(days=round(forward))
                ui.label(
                    "Oggi"
                    if forward <= 0
                    else f"Fra {format_number(forward, 0)} gg · {when.strftime('%d/%m/%Y')}"
                ).classes("text-xs t-muted")
                throttled_slider(
                    minimum=0,
                    maximum=max(dte, 1),
                    step=1,
                    value=forward,
                    on_value=set_forward,
                ).classes("w-full").props("color=primary")

        # Confronto
        username = auth.current_username()
        options = {NO_COMPARISON: "Nessun confronto"}
        if username:
            options.update({p.position_id: p.name for p in saved.list_for(username)})
        current = next(
            (k for k, v in options.items() if k and v == state.comparison_name),
            NO_COMPARISON,
        )
        ui.select(
            options,
            value=current,
            label="Confronta con",
            on_change=lambda e: set_comparison(e.value),
        ).props("dense outlined options-dense").classes("w-[220px]")

        # Esporta
        with ui.row().classes("gap-1 no-wrap"):
            ui.button(icon="image", on_click=export_png).props("flat dense round").classes(
                "t-muted"
            ).tooltip("Scarica il grafico come immagine")
            ui.button(
                icon="picture_as_pdf", on_click=lambda: ui.navigate.to("/stampa", new_tab=True)
            ).props("flat dense round").classes("t-muted").tooltip(
                "Riepilogo stampabile / salvabile in PDF"
            )
