"""Costruzione del diagramma di payoff per ECharts.

--- COSA FA QUESTO FILE ---
Produce UN DIZIONARIO. Nient'altro. Quel dizionario descrive il grafico —
quali linee, di che colore, con quali assi — e NiceGUI lo passa a ECharts, la
libreria JavaScript che lo disegna davvero nel browser.

Il vantaggio di questa separazione: si può leggere e modificare l'aspetto del
grafico senza sapere nulla di JavaScript, e senza che questo file possa
rompere qualcos'altro. Non calcola e non disegna: descrive.
"""

from __future__ import annotations

from typing import Any

from .formatting import format_number
from .state import Analytics, PositionState
from .theme import chart_palette


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


def build_payoff_option(
    state: PositionState, analytics: Analytics, palette: dict[str, str] | None = None
) -> dict[str, Any]:
    """Configurazione ECharts del diagramma di payoff.

    ``palette`` arriva da ``theme.chart_palette``: senza, si usa il tema scuro.
    """
    c = palette or chart_palette("dark")
    expiry = [[p.spot, round(p.expiry, 4)] for p in analytics.payoff]
    today = [[p.spot, round(p.today, 4)] for p in analytics.payoff]

    profit_area = [[p.spot, round(max(p.expiry, 0.0), 4)] for p in analytics.payoff]
    loss_area = [[p.spot, round(min(p.expiry, 0.0), 4)] for p in analytics.payoff]

    markers: list[dict[str, Any]] = [
        _marker(state.market.spot, c["spot"], f"spot {format_number(state.market.spot, 0)}", False)
    ]
    seen: set[float] = {round(state.market.spot, 4)}
    for leg in state.legs:
        strike = leg.entry_price if leg.__class__.__name__ == "StockLeg" else leg.strike  # type: ignore[union-attr]
        if round(strike, 4) not in seen and analytics.chart_low < strike < analytics.chart_high:
            seen.add(round(strike, 4))
            markers.append(_marker(strike, c["strike"], f"K {format_number(strike, 0)}"))
    for be in analytics.break_evens:
        if analytics.chart_low < be < analytics.chart_high:
            markers.append(_marker(be, c["profit"], f"BE {format_number(be, 1)}"))

    series: list[dict[str, Any]] = [
        {
            "name": "Profitto",
            "type": "line",
            "data": profit_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": c["profit"], "opacity": 0.16, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": "Perdita",
            "type": "line",
            "data": loss_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": c["loss"], "opacity": 0.16, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": "Valore oggi",
            "type": "line",
            "data": today,
            "showSymbol": False,
            "smooth": True,
            "lineStyle": {"color": c["today"], "width": 2, "type": "dashed"},
            "itemStyle": {"color": c["today"]},
            "z": 3,
        },
        {
            "name": "A scadenza",
            "type": "line",
            "data": expiry,
            "showSymbol": False,
            "lineStyle": {"color": c["expiry"], "width": 2.6},
            "itemStyle": {"color": c["expiry"]},
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
                "lineStyle": {"color": c["sim"], "width": 1.8, "type": "dotted"},
                "itemStyle": {"color": c["sim"]},
                "z": 2,
            },
        )

    if analytics.other_exercise is not None:
        style = "americane" if analytics.other_exercise == "american" else "europee"
        series.insert(
            2,
            {
                "name": f"Oggi se fossero {style}",
                "type": "line",
                "data": [
                    [p.spot, round(p.today_other, 4)]
                    for p in analytics.payoff
                    if p.today_other is not None
                ],
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"color": c["other"], "width": 2},
                "itemStyle": {"color": c["other"]},
                "z": 2,
            },
        )

    return {
        "backgroundColor": "transparent",
        "animation": False,
        "textStyle": {"fontFamily": c["font"]},
        "grid": {"left": 64, "right": 28, "top": 52, "bottom": 52},
        "legend": {
            "textStyle": {"color": c["axis"], "fontSize": 12},
            "top": 10,
            "right": 20,
            "icon": "roundRect",
            "itemWidth": 14,
            "itemHeight": 4,
            "itemGap": 18,
            "data": [s["name"] for s in series if not s.get("silent")],
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": c["tooltip_bg"],
            "borderColor": c["tooltip_border"],
            "borderRadius": 10,
            "padding": [8, 12],
            "extraCssText": "box-shadow: 0 6px 24px rgba(0,0,0,.18);",
            "textStyle": {"color": c["expiry"], "fontSize": 12, "fontFamily": c["font"]},
            "axisPointer": {"type": "line", "lineStyle": {"color": c["axis"]}},
        },
        "xAxis": {
            "type": "value",
            "min": round(analytics.chart_low, 2),
            "max": round(analytics.chart_high, 2),
            "name": "Prezzo del sottostante",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": c["axis"], "fontSize": 12},
            "axisLabel": {"color": c["axis"], "fontSize": 11},
            "axisLine": {"lineStyle": {"color": c["grid"]}},
            "splitLine": {"lineStyle": {"color": c["grid"]}},
        },
        "yAxis": {
            "type": "value",
            "name": "Profitto / Perdita",
            "nameTextStyle": {"color": c["axis"], "fontSize": 12},
            "axisLabel": {"color": c["axis"], "fontSize": 11},
            "axisLine": {"lineStyle": {"color": c["grid"]}},
            "splitLine": {"lineStyle": {"color": c["grid"]}},
        },
        "series": series,
    }
