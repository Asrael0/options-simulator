"""Interface panels, one per module.

The visual blocks of the simulator: market, strategies, legs, summary, Greeks,
scenario simulator, costs. Each panel is a function that receives the page
context and draws itself.

No panel does any financial maths: the numbers arrive ready-made from
``ctx.analytics``. Pages are composed by choosing which panels to show, with no
duplicated logic.

They are all re-exported here, so pages write ``from ..panels import ...``
without knowing which module holds each one.
"""

from __future__ import annotations

from .chart_controls import chart_controls_panel
from .costs import cost_panel
from .greeks import greeks_panel
from .heatmap import heatmap_intro_panel
from .legs import legs_panel
from .market import market_panel
from .positions import load_saved_into, saved_panel
from .scenario import scenario_panel
from .strategy import strategy_panel
from .summary import summary_panel

__all__ = [
    "chart_controls_panel",
    "cost_panel",
    "greeks_panel",
    "heatmap_intro_panel",
    "legs_panel",
    "load_saved_into",
    "market_panel",
    "saved_panel",
    "scenario_panel",
    "strategy_panel",
    "summary_panel",
]
