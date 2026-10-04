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
from .i18n import current_lang, tr
from .state import Analytics, Heatmap, PositionState
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


def scenario_label(state: PositionState, analytics: Analytics) -> str:
    """Nome della curva di scenario: dice cosa cambia rispetto a oggi."""
    parts = []
    if analytics.scenario.days > 0:
        parts.append(tr("fra {days} gg", days=format_number(analytics.scenario.days, 0)))
    if abs(analytics.scenario.iv - state.market.iv) > 1e-12:
        parts.append(f"IV {format_number(analytics.scenario.iv * 100, 0)}%")
    return tr("Scenario: {parts}", parts=" · ".join(parts))


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
    target = analytics.scenario.price
    if (
        abs(target - state.market.spot) > 1e-9
        and analytics.chart_low < target < analytics.chart_high
    ):
        markers.append(
            _marker(target, c["forward"], tr("scenario {price}", price=format_number(target, 0)))
        )
    for be in analytics.break_evens:
        if analytics.chart_low < be < analytics.chart_high:
            markers.append(_marker(be, c["profit"], f"BE {format_number(be, 1)}"))

    series: list[dict[str, Any]] = [
        {
            "name": tr("Profitto"),
            "type": "line",
            "data": profit_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": c["profit"], "opacity": 0.16, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": tr("Perdita"),
            "type": "line",
            "data": loss_area,
            "showSymbol": False,
            "lineStyle": {"width": 0},
            "areaStyle": {"color": c["loss"], "opacity": 0.16, "origin": "auto"},
            "silent": True,
            "z": 1,
        },
        {
            "name": tr("Valore oggi"),
            "type": "line",
            "data": today,
            "showSymbol": False,
            "smooth": True,
            "lineStyle": {"color": c["today"], "width": 2, "type": "dashed"},
            "itemStyle": {"color": c["today"]},
            "z": 3,
        },
        {
            "name": tr("A scadenza"),
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

    if analytics.scenario_curve:
        series.insert(
            2,
            {
                "name": scenario_label(state, analytics),
                "type": "line",
                "data": [
                    [p.spot, round(p.scenario, 4)]
                    for p in analytics.payoff
                    if p.scenario is not None
                ],
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"color": c["forward"], "width": 2.2},
                "itemStyle": {"color": c["forward"]},
                "z": 3,
            },
        )

    if analytics.comparison_name is not None:
        series.append(
            {
                "name": tr("Confronto: {name}", name=tr(analytics.comparison_name)),
                "type": "line",
                "data": [
                    [p.spot, round(p.compare, 4)] for p in analytics.payoff if p.compare is not None
                ],
                "showSymbol": False,
                "lineStyle": {"color": c["compare"], "width": 2, "type": [8, 4, 2, 4]},
                "itemStyle": {"color": c["compare"]},
                "z": 3,
            }
        )

    if analytics.other_exercise is not None:
        other_name = (
            tr("Oggi se fossero americane")
            if analytics.other_exercise == "american"
            else tr("Oggi se fossero europee")
        )
        series.insert(
            2,
            {
                "name": other_name,
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
            "name": tr("Prezzo del sottostante"),
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": c["axis"], "fontSize": 12},
            "axisLabel": {"color": c["axis"], "fontSize": 11},
            "axisLine": {"lineStyle": {"color": c["grid"]}},
            "splitLine": {"lineStyle": {"color": c["grid"]}},
        },
        "yAxis": {
            "type": "value",
            "name": tr("Profitto / Perdita"),
            "nameTextStyle": {"color": c["axis"], "fontSize": 12},
            "axisLabel": {"color": c["axis"], "fontSize": 11},
            "axisLine": {"lineStyle": {"color": c["grid"]}},
            "splitLine": {"lineStyle": {"color": c["grid"]}},
        },
        "series": series,
    }


def build_heatmap_option(
    state: PositionState, heatmap: Heatmap, palette: dict[str, str] | None = None
) -> dict[str, Any]:
    """Mappa di calore del P&L: prezzo in orizzontale, tempo in verticale."""
    c = palette or chart_palette("dark")
    dte = state.market.days_to_expiry
    x_labels = [format_number(p, 0) for p in heatmap.prices]
    y_labels = [
        tr("oggi")
        if d == 0
        else (tr("scadenza") if d >= dte else tr("+{days} gg", days=format_number(d, 0)))
        for d in heatmap.days
    ]
    # Perdite e profitti hanno scale separate: -1 è la perdita peggiore della
    # mappa, +1 il profitto migliore. Con un'unica scala, una perdita di 3 $
    # accanto a profitti di 40 $ sparirebbe nel colore neutro.
    flat = [v for line in heatmap.values for v in line]
    worst = -min(min(flat, default=0.0), 0.0) or 1.0
    best = max(max(flat, default=0.0), 0.0) or 1.0
    data = [
        [col, row, round(value, 2), value / worst if value < 0 else value / best]
        for row, line in enumerate(heatmap.values)
        for col, value in enumerate(line)
    ]
    axis = {
        "axisLabel": {"color": c["axis"], "fontSize": 11},
        "axisLine": {"lineStyle": {"color": c["grid"]}},
        "axisTick": {"show": False},
        "nameTextStyle": {"color": c["axis"], "fontSize": 12},
        "splitArea": {"show": False},
    }
    return {
        "backgroundColor": "transparent",
        "animation": False,
        "textStyle": {"fontFamily": c["font"]},
        "grid": {"left": 76, "right": 24, "top": 16, "bottom": 96},
        "tooltip": {
            "position": "top",
            "backgroundColor": c["tooltip_bg"],
            "borderColor": c["tooltip_border"],
            "textStyle": {"color": c["expiry"], "fontSize": 12},
            ":formatter": (
                "p => `PRICE ${XS[p.value[0]]} · ${YS[p.value[1]]}<br>`"
                " + `<b>P&L ${p.value[2].toLocaleString('LOCALE',"
                " {minimumFractionDigits: 2, maximumFractionDigits: 2})}</b>`"
            )
            .replace("PRICE", tr("Prezzo"))
            .replace("LOCALE", "en-US" if current_lang() == "en" else "it-IT")
            .replace("XS", str(x_labels))
            .replace("YS", str(y_labels)),
        },
        "xAxis": {
            "type": "category",
            "data": x_labels,
            "name": tr("Prezzo del sottostante"),
            "nameLocation": "middle",
            "nameGap": 30,
            **axis,
        },
        "yAxis": {"type": "category", "data": y_labels, "inverse": True, **axis},
        "visualMap": {
            "min": -1,
            "max": 1,
            "dimension": 3,
            "calculable": False,
            "orient": "horizontal",
            "left": "center",
            "bottom": 4,
            "itemHeight": 220,
            "textStyle": {"color": c["axis"]},
            "text": [
                tr("profitto max {value}", value=format_number(best, 2)),
                tr("perdita max {value}", value=format_number(-worst, 2)),
            ],
            "inRange": {"color": [c["loss"], c["neutral"], c["profit"]]},
        },
        "series": [
            {
                "type": "heatmap",
                "data": data,
                "itemStyle": {"borderColor": c["surface"], "borderWidth": 1.5, "borderRadius": 3},
                "emphasis": {"itemStyle": {"borderColor": c["expiry"], "borderWidth": 1.5}},
            }
        ],
    }
