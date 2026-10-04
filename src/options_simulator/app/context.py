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
        self._charts: list[_Chart] = []
        # Timer dell'animazione "scorri il tempo": lo crea la pagina.
        self.animation: ui.timer | None = None
        # Grafico principale, per esportarlo come immagine.
        self.main_chart: ui.echart | None = None

    def panel(self, render: PanelRenderer) -> None:
        """Disegna un pannello e lo registra per gli aggiornamenti futuri."""
        refreshable = ui.refreshable(partial(render, self))
        self._panels.append(refreshable)
        refreshable()

    def chart(
        self,
        builder: ChartBuilder,
        classes: str,
        *,
        active: Callable[[], bool] | None = None,
    ) -> ui.echart:
        """Grafico che si aggiorna con la posizione.

        ``active`` serve ai grafici costosi: se restituisce ``False`` (per
        esempio perché la scheda che lo contiene è chiusa) l'aggiornamento
        viene rimandato a quando ``refresh_charts`` lo trova di nuovo attivo.
        """
        visible = active is None or active()
        options = builder(self.state, self.analytics) if visible else {}
        element = ui.echart(options).classes(classes)
        self._charts.append(_Chart(element, builder, active, stale=not visible))
        return element

    def refresh_charts(self) -> None:
        """Aggiorna i grafici rimasti indietro mentre erano nascosti."""
        for chart in self._charts:
            if chart.stale:
                self._update(chart)

    def _update(self, chart: _Chart) -> None:
        if chart.active is not None and not chart.active():
            chart.stale = True
            return
        chart.element.options.clear()
        chart.element.options.update(chart.builder(self.state, self.analytics))
        chart.element.update()
        chart.stale = False

    def rerender(self) -> None:
        """Ricalcola una volta sola, poi aggiorna tutto ciò che è registrato."""
        self.analytics = compute(self.state)
        for chart in self._charts:
            self._update(chart)
        for refreshable in self._panels:
            refreshable.refresh()


class _Chart:
    __slots__ = ("active", "builder", "element", "stale")

    def __init__(
        self,
        element: ui.echart,
        builder: ChartBuilder,
        active: Callable[[], bool] | None,
        *,
        stale: bool,
    ) -> None:
        self.element = element
        self.builder = builder
        self.active = active
        self.stale = stale
