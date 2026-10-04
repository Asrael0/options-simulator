"""Page context: keeps state, derived values and refreshing together.

The problem: a page shows eight panels that all depend on the same numbers, and
moving a slider must refresh all of them. If each one recomputed on its own, a
single move would cost eight recomputations instead of one.

The solution: ``PageContext`` holds the state, the derived numbers and a LIST of
the panels drawn. When something changes, ``rerender()`` recomputes ONCE and then
tells every panel to redraw from the result that is already there.
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
    """State + analytics + registry of the panels to refresh."""

    def __init__(self, state: PositionState) -> None:
        self.state = state
        self.analytics: Analytics = compute(state)
        self._panels: list[Any] = []
        self._charts: list[_Chart] = []
        # Timer of the "run time forward" animation: created by the page.
        self.animation: ui.timer | None = None
        # Main chart, so it can be exported as an image.
        self.main_chart: ui.echart | None = None

    def panel(self, render: PanelRenderer) -> None:
        """Draw a panel and register it for future refreshes."""
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
        """Chart that follows the position.

        ``active`` is for expensive charts: when it returns ``False`` (for example
        because the tab holding the chart is closed) the update is postponed
        until ``refresh_charts`` finds it active again.
        """
        visible = active is None or active()
        options = builder(self.state, self.analytics) if visible else {}
        element = ui.echart(options).classes(classes)
        self._charts.append(_Chart(element, builder, active, stale=not visible))
        return element

    def refresh_charts(self) -> None:
        """Update the charts that fell behind while hidden."""
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
        """Recompute once, then refresh everything registered."""
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
