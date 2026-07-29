"""Contesto di pagina: tiene insieme stato, valori derivati e aggiornamento.

Il problema che risolve: una pagina mostra molti pannelli che dipendono tutti
dagli stessi numeri. Se ogni pannello ricalcolasse per conto suo, muovere uno
slider costerebbe otto volte il dovuto. Qui il calcolo avviene UNA volta in
``rerender()``, e i pannelli si limitano a leggere ``ctx.analytics``.

NOTA DI PYTHON — ``functools.partial``.

``ui.refreshable`` vuole una funzione senza argomenti, ma i pannelli hanno
bisogno del contesto. ``partial(render, self)`` costruisce una nuova funzione
con il primo argomento già fissato: è il modo pulito di "pre-riempire" un
parametro senza scrivere una lambda per ognuno.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from nicegui import ui

from .state import Analytics, PositionState, compute

#: Un pannello è una funzione che disegna se stessa leggendo il contesto.
PanelRenderer = Callable[["PageContext"], None]
#: Un costruttore di grafico produce il dizionario di opzioni ECharts.
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
