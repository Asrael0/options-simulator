"""«Underlying and market» panel: ticker, name, spot, days, IV, rate, style."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ...pricing import TYPICAL_CRASHES, StockLeg
from ..context import PageContext
from ..formatting import (
    format_expiry,
)
from ..i18n import tr
from ..tickers import company_name, display_symbol
from ..widgets import (
    CARD,
    FAINT,
    MUTED,
    card_title,
    commit_on_leave,
    throttled_slider,
    ticker_search,
)


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
        card_title(tr("Sottostante e mercato"), "tune")
        with ui.row().classes("w-full gap-2 no-wrap"):
            # Ticker and name are linked: picking a stock in either field fills
            # both, with the catalogue spellings.
            ticker_search(
                label=tr("Ticker"),
                value=display_symbol(state.ticker),
                on_pick=lambda s: _set_symbol(ctx, s),
                classes="w-[38%] shrink-0",
                commit_on_blur=True,
            )
            ticker_search(
                label=tr("Nome"),
                value=state.name,
                on_pick=lambda s: _set_symbol(ctx, s),
                on_text=lambda t: _set_text(ctx, "name", t),
                classes="grow",
                commit_on_blur=True,
                mode="name",
                align_right=True,
            )

        commit_on_leave(
            ui.number(tr("Prezzo spot"), value=m.spot, step=0.5, format="%.2f")
            .classes("w-full")
            .props("dense outlined suffix=$"),
            lambda v: set_field("spot", v),
        )
        throttled_slider(
            minimum=max(min(references) * 0.5, 1.0),
            maximum=max(references) * 1.5,
            step=0.5,
            value=m.spot,
            on_value=lambda v: set_field("spot", v),
        ).classes("w-full")

        commit_on_leave(
            ui.number(tr("Giorni alla scadenza"), value=m.days_to_expiry, step=1, format="%.0f")
            .classes("w-full")
            .props(
                'dense outlined suffix="'
                + tr("gg · scade {date}", date=format_expiry(m.days_to_expiry))
                + '"'
            ),
            lambda v: set_field("days_to_expiry", v),
        )
        throttled_slider(
            minimum=0,
            maximum=365,
            step=1,
            value=m.days_to_expiry,
            on_value=lambda v: set_field("days_to_expiry", v),
        ).classes("w-full")

        commit_on_leave(
            ui.number(tr("Volatilità implicita (IV)"), value=m.iv * 100, step=1, format="%.1f")
            .classes("w-full")
            .props("dense outlined suffix=%"),
            lambda v: set_field("iv", (v or 0) / 100),
        )
        throttled_slider(
            minimum=1,
            maximum=150,
            step=1,
            value=m.iv * 100,
            on_value=lambda v: set_field("iv", v / 100),
        ).classes("w-full")

        with ui.row().classes("w-full gap-2 no-wrap"):
            commit_on_leave(
                ui.number(
                    tr("Tasso risk-free"), value=m.risk_free_rate * 100, step=0.25, format="%.2f"
                )
                .classes("grow")
                .props("dense outlined suffix=%"),
                lambda v: set_field("risk_free_rate", (v or 0) / 100),
            )
            commit_on_leave(
                ui.number(
                    tr("Dividend yield"), value=m.dividend_yield * 100, step=0.25, format="%.2f"
                )
                .classes("grow")
                .props("dense outlined suffix=%"),
                lambda v: set_field("dividend_yield", (v or 0) / 100),
            )

        ui.separator().classes("my-3")
        ui.label(tr("Stile di esercizio")).classes(MUTED + " font-medium")
        ui.toggle(
            {"european": tr("Europea"), "american": tr("Americana")},
            value=state.exercise,
            on_change=lambda e: _set_exercise(ctx, e.value),
        ).props("dense no-caps unelevated spread toggle-color=primary").classes("w-full sim-seg")
        european = state.exercise == "european"
        merton = state.active_jumps is not None
        ui.label(
            tr(
                "Esercitabile solo a scadenza. Prezzata con Merton: Black-Scholes più "
                "salti improvvisi."
            )
            if merton
            else tr(
                "Esercitabile solo a scadenza. Prezzata con Black-Scholes-Merton (formula chiusa)."
            )
            if european
            else tr(
                "Esercitabile in qualsiasi momento. Prezzata con albero binomiale "
                "CRR: include il valore dell'esercizio anticipato, visibile "
                "soprattutto sulle put ITM."
            )
        ).classes(FAINT)

        ui.label(tr("Modello di prezzo")).classes(MUTED + " font-medium mt-3")
        ui.toggle(
            {"bsm": "Black-Scholes", "merton": tr("Merton (con salti)")},
            value=state.model if european else "bsm",
            on_change=lambda e: _set_model(ctx, e.value),
        ).props(
            "dense no-caps unelevated spread toggle-color=primary"
            + ("" if european else " disable")
        ).classes("w-full sim-seg")
        if not european:
            ui.label(
                tr("Merton vale solo per le opzioni europee: scegli «Europea» per usarlo.")
            ).classes(FAINT)
        elif merton:
            _jump_fields(ctx)

        if merton:
            return
        other = tr("americane") if state.exercise == "european" else tr("europee")
        ui.switch(
            tr("Confronta sul grafico: se fossero {other}", other=other),
            value=state.compare_exercise,
            on_change=lambda e: _set_compare(ctx, e.value),
        ).props("dense").classes("mt-1 text-xs")
        if state.compare_exercise:
            ui.label(
                tr(
                    "La curva verde acqua usa gli stessi premi pagati: la distanza dalla "
                    "viola è solo il valore dell'esercizio anticipato. Per una call senza "
                    "dividendi le due curve coincidono."
                )
            ).classes(FAINT)


def _jump_fields(ctx: PageContext) -> None:
    """The three jump parameters, in plain units: jumps a year, size, variability."""
    jumps = ctx.state.jumps

    def set_jump(name: str, value: Any, scale: float = 1.0) -> None:
        if value is None:
            return
        ctx.state.set_jumps(**{name: float(value) / scale})
        ctx.rerender()

    def typical() -> None:
        ctx.state.jumps = TYPICAL_CRASHES
        ctx.rerender()

    with ui.row().classes("w-full gap-2 no-wrap mt-1"):
        commit_on_leave(
            ui.number(tr("Salti/anno"), value=round(jumps.intensity, 2), step=0.1, format="%.2f")
            .classes("grow basis-0")
            .props("dense outlined"),
            lambda v: set_jump("intensity", v),
        )
        commit_on_leave(
            ui.number(
                tr("Salto medio"), value=round(jumps.expected_jump * 100, 1), step=1, format="%.1f"
            )
            .classes("grow basis-0")
            .props("dense outlined suffix=%"),
            lambda v: set_jump("size", v, 100.0),
        )
        commit_on_leave(
            ui.number(tr("Variabilità"), value=round(jumps.vol * 100, 1), step=1, format="%.1f")
            .classes("grow basis-0")
            .props("dense outlined suffix=%"),
            lambda v: set_jump("vol", v, 100.0),
        )
    ui.label(
        tr(
            "Con Merton la IV qui sopra è la volatilità senza salti: i salti si aggiungono, "
            "quindi le opzioni costano di più, soprattutto le put lontane. Salto medio "
            "negativo = crollo."
        )
    ).classes(FAINT)
    ui.button(tr("Valori tipici dell'S&P 500"), icon="restart_alt", on_click=typical).props(
        "flat dense no-caps color=primary"
    ).classes("text-xs self-start")


def _set_model(ctx: PageContext, value: str) -> None:
    ctx.state.model = "merton" if value == "merton" else "bsm"
    ctx.rerender()


def _set_symbol(ctx: PageContext, symbol: str) -> None:
    """Set ticker and name together, from the catalogue.

    The ticker is stored in its display spelling (``SPX``, never ``_SPX`` or
    ``^SPX``). If the symbol is not in the catalogue the name becomes the symbol
    itself, so a different company's name is never left behind.
    """
    shown = display_symbol(symbol)
    if not shown:
        return
    ctx.state.ticker = shown
    ctx.state.name = company_name(symbol) or shown
    ctx.rerender()


def _set_text(ctx: PageContext, attribute: str, value: str) -> None:
    """Free text (a hand-typed name): it enters no calculation."""
    setattr(ctx.state, attribute, value)
    ctx.rerender()


def _set_exercise(ctx: PageContext, value: str) -> None:
    ctx.state.exercise = value  # type: ignore[assignment]
    ctx.rerender()


def _set_compare(ctx: PageContext, value: bool) -> None:
    ctx.state.compare_exercise = value
    ctx.rerender()
