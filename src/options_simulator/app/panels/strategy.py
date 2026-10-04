"""Pannello «Strategie precostruite» e premi d'ingresso congelati."""

from __future__ import annotations

from nicegui import ui

from ..context import PageContext
from ..formatting import (
    format_number,
    format_percent,
)
from ..strategies import (
    CUSTOM_STRATEGY,
    CUSTOM_STRATEGY_DESCRIPTION,
    CUSTOM_STRATEGY_NAME,
    STRATEGIES,
)
from ..widgets import (
    CARD,
    FAINT,
    MUTED,
    card_title,
)


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
        card_title("Strategie precostruite", "auto_awesome")
        options = {key: s.name for key, s in STRATEGIES.items()}
        if state.strategy_key not in options:
            options = {CUSTOM_STRATEGY: CUSTOM_STRATEGY_NAME, **options}
        ui.select(
            options,
            value=state.strategy_key if state.strategy_key in options else CUSTOM_STRATEGY,
            on_change=lambda e: apply(e.value),
        ).classes("w-full").props("dense outlined")
        strategy = STRATEGIES.get(state.strategy_key)
        ui.label(
            strategy.description if strategy is not None else CUSTOM_STRATEGY_DESCRIPTION
        ).classes(FAINT)

        ui.separator().classes("my-3")
        ui.label("Premi d'ingresso").classes(MUTED + " font-medium")
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
                ui.label(
                    f"Premi fissati a: spot {format_number(entry.spot, 2)} $ · "
                    f"IV {format_percent(entry.iv, 1)} · "
                    f"{format_number(entry.days_to_expiry, 0)} gg. "
                    "Anche le gambe aggiunte ora usano questi valori."
                ).classes("text-[11px] leading-relaxed mt-1 px-2.5 py-1.5 sim-warn")
            ui.button(
                "Rifissa i premi ai prezzi correnti", icon="push_pin", on_click=reprice
            ).props("outline dense no-caps color=primary").classes("text-xs px-3 mt-1")
