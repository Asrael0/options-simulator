"""«Volatility» tab: implied against historical, expensive or cheap."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ...formatting import format_number, format_percent, format_short_date
from ...i18n import tr
from ...theme import chart_palette
from ...tickers import display_symbol
from ...widgets import (
    FAINT,
    card_title,
    stat,
)
from .view import MarketView

VERDICTS: dict[str, tuple[str, str, str]] = {
    # verdict -> (title, colour, explanation)
    "expensive": (
        "Opzioni care",
        "var(--loss)",
        "Il mercato si aspetta più movimento di quello che il titolo ha fatto "
        "nell'ultimo mese, oppure c'è un evento in arrivo (per esempio gli utili "
        "trimestrali). Chi vende opzioni incassa premi alti; chi le compra paga caro "
        "e rischia il vol crush quando l'evento passa.",
    ),
    "average": (
        "Opzioni nella media",
        "var(--info)",
        "La volatilità implicita è in linea con quella realizzata, con il piccolo "
        "sovrapprezzo che il mercato chiede di solito. Nessun vantaggio evidente né "
        "per chi compra né per chi vende.",
    ),
    "cheap": (
        "Opzioni economiche",
        "var(--profit)",
        "Il mercato prezza meno movimento di quello che il titolo sta facendo davvero. "
        "Comprare opzioni costa poco rispetto all'agitazione recente; vendere "
        "opzioni incassa poco per il rischio che si prende.",
    ),
}


def render_volatility(view: MarketView) -> None:
    card_title(
        tr("Volatilità implicita contro storica"),
        "show_chart",
        tone="violet",
        subtitle=tr(
            "La IV è quanto il mercato si aspetta che il titolo si muova; la "
            "storica è quanto si è mosso davvero. Confrontarle dice se le opzioni sono "
            "care o economiche."
        ),
    )
    if view.vol_loading:
        with ui.row().classes("items-center gap-2"):
            ui.spinner(size="sm").classes("t-accent")
            ui.label(tr("Scarico lo storico dei prezzi…")).classes("text-sm t-muted")
        return
    if view.vol_error:
        ui.label(view.vol_error).classes("text-sm t-muted")
        return
    report = view.vol
    if report is None:
        ui.label(tr("Carica un titolo per vedere la sua volatilità.")).classes("text-sm t-muted")
        return

    if report.verdict is not None and report.ratio is not None and report.iv is not None:
        title, color, text = VERDICTS[report.verdict]
        with (
            ui.column()
            .classes("w-full gap-1 sim-stat mb-2")
            .style(
                f"border-color: {color}; background: color-mix(in srgb, {color} 8%, var(--surface-2))"  # noqa: E501
            )
        ):
            ui.label(tr(title)).classes("t-serif text-[24px] leading-tight").style(
                f"color: {color}"
            )
            ui.label(
                tr(
                    "La IV a 30 giorni ({iv}) è {ratio} volte la volatilità realizzata "
                    "nell'ultimo mese ({hv20}). {text}",
                    iv=format_percent(report.iv, 1),
                    ratio=format_number(report.ratio, 2),
                    hv20=format_percent(report.hv20, 1),
                    text=tr(text),
                )
            ).classes("text-sm t-text2 leading-relaxed")

    with ui.element("div").classes("w-full grid gap-2 grid-cols-2 md:grid-cols-3"):
        stat(
            tr("Implicita a 30 giorni"),
            format_percent(report.iv, 1) if report.iv is not None else "—",
            sub=tr("quanto il mercato si aspetta"),
            icon="visibility",
        )
        stat(
            tr("Storica 1 mese"),
            format_percent(report.hv20, 1),
            sub=tr("20 giorni di borsa"),
            icon="history",
        )
        stat(
            tr("Storica 3 mesi"),
            format_percent(report.hv60, 1),
            sub=tr("60 giorni di borsa"),
            icon="history",
        )
        stat(
            tr("Storica 1 anno"),
            format_percent(report.hv252, 1),
            sub=tr("252 giorni di borsa"),
            icon="history",
        )
        stat(
            tr("Implicita / storica"),
            tr("{ratio}×", ratio=format_number(report.ratio, 2))
            if report.ratio is not None
            else "—",
            sub=tr("sopra 1 = il mercato prevede più movimento"),
            icon="balance",
        )
        stat(
            tr("Posizione nell'anno"),
            format_percent(report.percentile, 0) if report.percentile is not None else "—",
            sub=tr("giorni dell'ultimo anno con storica più bassa della IV di oggi"),
            icon="leaderboard",
        )

    c = chart_palette()
    days = [format_short_date(d, year=True) for d, _ in report.rolling]
    price_by_day = {p.day: p.close for p in report.prices}
    series: list[dict[str, Any]] = [
        {
            "name": tr("Storica a 30 giorni"),
            "type": "line",
            "data": [round(v * 100, 2) for _, v in report.rolling],
            "showSymbol": False,
            "lineStyle": {"color": c["forward"], "width": 2},
            "itemStyle": {"color": c["forward"]},
            "areaStyle": {"color": c["forward"], "opacity": 0.08},
        },
        {
            "name": tr("Prezzo {symbol}", symbol=display_symbol(report.source)),
            "type": "line",
            "yAxisIndex": 1,
            "data": [price_by_day.get(d) for d, _ in report.rolling],
            "showSymbol": False,
            "lineStyle": {"color": c["axis"], "width": 1.2, "opacity": 0.7},
            "itemStyle": {"color": c["axis"]},
        },
    ]
    if report.iv is not None:
        series.append(
            {
                "name": tr("Implicita di oggi"),
                "type": "line",
                "data": [round(report.iv * 100, 2)] * len(days),
                "showSymbol": False,
                "lineStyle": {"color": c["today"], "width": 2, "type": "dashed"},
                "itemStyle": {"color": c["today"]},
            }
        )
    ui.label(tr("Volatilità storica nell'ultimo anno, contro la implicita di oggi")).classes(
        "text-sm font-semibold t-text mt-3"
    )
    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": False,
            "textStyle": {"fontFamily": c["font"]},
            "grid": {"left": 48, "right": 56, "top": 36, "bottom": 30},
            "legend": {"top": 4, "right": 8, "textStyle": {"color": c["axis"], "fontSize": 11}},
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": c["tooltip_bg"],
                "borderColor": c["tooltip_border"],
                "textStyle": {"color": c["expiry"], "fontSize": 12},
            },
            "xAxis": {
                "type": "category",
                "data": days,
                "axisLabel": {"color": c["axis"], "fontSize": 10},
                "axisLine": {"lineStyle": {"color": c["grid"]}},
            },
            "yAxis": [
                {
                    "type": "value",
                    "scale": True,
                    "axisLabel": {"color": c["axis"], "fontSize": 10, "formatter": "{value}%"},
                    "splitLine": {"lineStyle": {"color": c["grid"]}},
                },
                {
                    "type": "value",
                    "scale": True,
                    "axisLabel": {"color": c["axis"], "fontSize": 10},
                    "splitLine": {"show": False},
                },
            ],
            "series": series,
        }
    ).classes("w-full h-[320px]")

    proxy = display_symbol(report.source) != display_symbol(view.chain.ticker if view.chain else "")
    ui.label(
        tr(
            "Storica = deviazione standard dei rendimenti giornalieri, annualizzata (×√252). "
            "La IV sta di solito un po' sopra la storica anche in tempi normali: chi vende "
            "opzioni chiede un premio per il rischio di movimenti improvvisi. Per questo "
            "«care» scatta solo quando la IV supera la storica di oltre il 25%."
        )
        + (
            tr(
                " Per gli indici CBOE non fornisce lo storico: si usa "
                "{display_symbol}, l'ETF che li replica.",
                display_symbol=display_symbol(report.source),
            )
            if proxy
            else ""
        )
    ).classes(FAINT + " mt-2")
