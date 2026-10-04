"""Pannello «Greche aggregate della posizione»."""

from __future__ import annotations

from nicegui import ui

from ..context import PageContext
from ..formatting import (
    format_number,
)
from ..widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    card_title,
)

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


def greeks_panel(ctx: PageContext) -> None:
    g = ctx.analytics.greeks
    with ui.card().classes(CARD):
        card_title(
            "Greche aggregate della posizione",
            "functions",
            subtitle="Somma delle greche di tutte le gambe, con segno e quantità.",
        )
        with ui.element("div").classes(
            "w-full grid gap-3 grid-cols-1 sm:grid-cols-2 xl:grid-cols-5"
        ):
            for symbol, name, attribute, unit, description in GREEK_ROWS:
                value = getattr(g, attribute)
                with ui.column().classes("gap-1 sim-stat min-w-0"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.label(symbol).classes("t-serif text-[20px] t-accent leading-none")
                        ui.label(name).classes("sim-stat-label")
                    with ui.row().classes("items-baseline gap-1.5 no-wrap"):
                        ui.label(format_number(value, 4)).classes("sim-stat-value").style(
                            f"color: {COLOR_PROFIT if value >= 0 else COLOR_LOSS}"
                        )
                        if unit:
                            ui.label(unit).classes("text-[11px] t-muted")
                    ui.label(description).classes("text-[11px] t-faint leading-relaxed")
