"""Intestazione della scheda «Mappa P&L»."""

from __future__ import annotations

from ..context import PageContext
from ..widgets import (
    card_title,
)


def heatmap_intro_panel(ctx: PageContext) -> None:
    card_title(
        "Mappa del P&L: prezzo × tempo",
        "grid_on",
        subtitle="Ogni casella è il guadagno o la perdita per unità, se il titolo "
        "valesse quel prezzo in quel giorno (IV e tasso fermi).",
    )
