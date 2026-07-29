"""Costruzione del diagramma di payoff per ECharts.

NiceGUI include ECharts, quindi il grafico è interattivo (zoom, tooltip che
segue il cursore) senza aggiungere dipendenze. Questo modulo produce solo il
dizionario di configurazione: non tocca l'interfaccia e non calcola nulla di
finanziario, così resta facile da leggere e da modificare.
"""

from __future__ import annotations

from typing import Any

from .formatting import format_number
from .state import Analytics, PositionState

COLOR_EXPIRY = "#e6e9f0"
COLOR_TODAY = "#b07dff"
COLOR_SIM = "#ff9f1c"
COLOR_PROFIT = "#3ddc97"
COLOR_LOSS = "#ff5d6c"
COLOR_SPOT = "#5b8def"
COLOR_STRIKE = "#f0a500"
COLOR_AXIS = "#8b93a7"
COLOR_GRID = "#1e222d"


def _marker(value: float, color: str, label: str, dashed: bool = True) -> dict[str, Any]:
    return {
        "xAxis": value,
        "lineStyle": {
            "color": color,
            "width": 1.5,
            "type": "dashed" if dashed else "solid",
            "opacity": 0.8,
        },
        "label": {"formatter": label, "color": color, "fontSize": 10, "position": "insideEndTop"},
    }


def build_payoff_option(state: PositionState, analytics: Analytics) -> dict[str, Any]:
    """Configurazione ECharts del diagramma di payoff."""
    expiry = [[p.spot, round(p.expiry, 4)] for p in analytics.payoff]
    today = [[p.spot, round(p.today, 4)] for p in analytics.payoff]

    # Serie separate per riempire di verde sopra lo zero e di rosso sotto.
    # `origin: "auto"` fa partire il riempimento dalla linea dello zero.
    profit_area = [[p.spot, round(max(p.expiry, 0.0), 4)] for p in analytics.payoff]
    loss_area = [[p.spot, round(min(p.expiry, 0.0), 4)] for p in analytics.payoff]

    markers: list[dict[str, Any]] = [
        _marker(state.market.spot, COLOR_SPOT, f"spot {format_number(state.market.spot, 0)}", False)
    ]
    seen: set[float] = {round(state.market.spot, 4)}
    for leg in state.legs:
        strike = leg.entry_price if leg.__class__.__name__ == "StockLeg" else leg.strike  # type: ignore[union-attr]
        if round(strike, 4) not in seen and analytics.chart_low < strike < analytics.chart_high:
            seen.add(round(strike, 4))
            markers.append(_marker(strike, COLOR_STRIKE, f"K {format_number(strike, 0)}"))
    for be in analytics.break_evens:
        if analytics.chart_low < be < analytics.chart_high:
            markers.append(_marker(be, COLOR_PROFIT, f"BE {format_number(be, 1)}"))

    series: list[dict[str, Any]] = [
        {
            "name": "Profitto",
            "type": "line",
            "data": profit_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": COLOR_PROFIT, "opacity": 0.18, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": "Perdita",
            "type": "line",
            "data": loss_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": COLOR_LOSS, "opacity": 0.18, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": "Valore oggi",
            "type": "line",
            "data": today,
            "showSymbol": False,
            "smooth": True,
            "lineStyle": {"color": COLOR_TODAY, "width": 2, "type": "dashed"},
            "z": 3,
        },
        {
            "name": "A scadenza",
            "type": "line",
            "data": expiry,
            "showSymbol": False,
            "lineStyle": {"color": COLOR_EXPIRY, "width": 2.6},
            "z": 4,
            "markLine": {
                "silent": True,
                "symbol": "none",
                "data": markers,
                "animation": False,
            },
        },
    ]

    if analytics.sim_iv_differs:
        series.insert(
            2,
            {
                "name": f"Oggi @ IV {format_number(state.iv_sim * 100, 0)}%",
                "type": "line",
                "data": [[p.spot, round(p.today_sim, 4)] for p in analytics.payoff],
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"color": COLOR_SIM, "width": 1.8, "type": "dotted"},
                "z": 2,
            },
        )

    return {
        "backgroundColor": "transparent",
        "animation": False,
        "grid": {"left": 62, "right": 24, "top": 44, "bottom": 48},
        "legend": {
            "textStyle": {"color": COLOR_AXIS, "fontSize": 11},
            "top": 4,
            "data": [s["name"] for s in series if not s.get("silent")],
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "#11141c",
            "borderColor": "#2a2f3a",
            "textStyle": {"color": COLOR_EXPIRY, "fontSize": 12},
            "axisPointer": {"type": "line", "lineStyle": {"color": COLOR_AXIS}},
        },
        "xAxis": {
            "type": "value",
            "min": round(analytics.chart_low, 2),
            "max": round(analytics.chart_high, 2),
            "name": "Prezzo del sottostante",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": COLOR_AXIS, "fontSize": 12},
            "axisLabel": {"color": COLOR_AXIS, "fontSize": 11},
            "axisLine": {"lineStyle": {"color": COLOR_GRID}},
            "splitLine": {"lineStyle": {"color": COLOR_GRID, "type": "dashed"}},
        },
        "yAxis": {
            "type": "value",
            "name": "Profitto / Perdita",
            "nameTextStyle": {"color": COLOR_AXIS, "fontSize": 12},
            "axisLabel": {"color": COLOR_AXIS, "fontSize": 11},
            "axisLine": {"lineStyle": {"color": COLOR_GRID}},
            "splitLine": {"lineStyle": {"color": COLOR_GRID, "type": "dashed"}},
        },
        "series": series,
    }
