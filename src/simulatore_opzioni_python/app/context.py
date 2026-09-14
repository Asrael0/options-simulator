"""Contesto di pagina: tiene insieme stato, valori derivati e aggiornamento.

--- COSA FA QUESTO FILE ---
È il motore dell'aggiornamento dell'interfaccia.

Il problema: una pagina mostra otto pannelli che dipendono tutti dagli stessi
numeri. Muovendo uno slider devono aggiornarsi tutti. Se ognuno ricalcolasse
per conto suo, un movimento costerebbe otto ricalcoli invece di uno.

La soluzione: `PageContext` tiene lo stato, i numeri derivati, e un ELENCO dei
pannelli disegnati. Quando qualcosa cambia, `rerender()` ricalcola UNA volta e
poi dice a ogni pannello di ridisegnarsi leggendo il risultato già pronto.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from nicegui import ui

from .state import Analytics, PositionState, compute

PanelRenderer = Callable[["PageContext"], None]
ChartBuilder = Callable[[PositionState, Analytics], dict[str, Any]]


class PageContext:
    """Stato + analytics + registro dei pannelli da aggiornare."""

    def __init__(self, state: PositionState) -> None:
        self.state = state
        self.analytics: Analytics = compute(state)
        self._panels: list[Any] = []
        self._charts: list[tuple[ui.echart, ChartBuilder]] = []

    def panel(self, render: PanelRenderer) -> None:
        """Disegna un pannello e lo registra per gli aggiornamenti futuri."""
        refreshable = ui.refreshable(partial(render, self))
        self._panels.append(refreshable)
        refreshable()

    def chart(self, builder: ChartBuilder, classes: str) -> ui.echart:
        element = ui.echart(builder(self.state, self.analytics)).classes(classes)
        self._charts.append((element, builder))
        return element

    def rerender(self) -> None:
        """Ricalcola una volta sola, poi aggiorna tutto ciò che è registrato."""
        self.analytics = compute(self.state)
        for element, builder in self._charts:
            element.options.clear()
            element.options.update(builder(self.state, self.analytics))
            element.update()
        for refreshable in self._panels:
            refreshable.refresh()
