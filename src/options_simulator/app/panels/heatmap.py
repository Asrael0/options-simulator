"""Intestazione della scheda «Mappa P&L»."""

from __future__ import annotations

from ..context import PageContext
from ..i18n import tr
from ..widgets import (
    card_title,
)


def heatmap_intro_panel(ctx: PageContext) -> None:
    card_title(
        tr("Mappa del P&L: prezzo × tempo"),
        "grid_on",
        subtitle=tr(
            "Ogni casella è il guadagno o la perdita per unità, se il titolo "
            "valesse quel prezzo in quel giorno (IV e tasso fermi)."
        ),
    )
