"""«Model vs market» tab: a single volatility against real prices."""

from __future__ import annotations

from typing import Any

from nicegui import run, ui

from ....pricing import MertonFit
from ...formatting import format_number, format_percent, format_signed_money
from ...i18n import tr
from ...jumps import calibrate_chain
from ...market_data import (
    ModelRow,
    model_vs_market,
)
from ...theme import chart_palette
from ...widgets import (
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    card_title,
    stat,
    throttled_slider,
)
from .view import MarketView, price_text


def render_comparison(view: MarketView, refresh: Any) -> None:
    chain, expiry = view.chain, view.expiry
    if chain is None or expiry is None:
        return
    atm = chain.atm_iv(expiry) or chain.iv30 or 0.3
    iv = view.model_iv if view.model_iv is not None else atm

    def set_iv(value: float) -> None:
        view.model_iv = value / 100
        refresh()

    def set_rate(value: Any) -> None:
        if value is not None:
            view.manual_rate = float(value) / 100
            refresh()

    def set_dividend(value: Any) -> None:
        if value is not None:
            view.manual_dividend = float(value) / 100
            refresh()

    def set_exercise(value: str) -> None:
        view.manual_exercise = value
        refresh()

    def use_market_values() -> None:
        view.reset_carry()
        refresh()

    def reset_iv() -> None:
        view.model_iv = None
        refresh()

    # Calibration takes a second or two: it runs off the UI loop, and messages
    # are attached to the page layout because this tab redraws meanwhile.
    root = ui.context.client.layout

    async def calibrate() -> None:
        view.calibrating = True
        refresh()
        fit = await run.io_bound(calibrate_chain, chain, expiry, view.rate, view.dividend(expiry))
        view.calibrating = False
        view.merton, view.merton_key = fit, (chain.ticker, expiry)
        if fit is None:
            with root:
                ui.notify(
                    tr("Troppo poche opzioni quotate su questa scadenza per calibrare i salti."),
                    type="warning",
                )
        refresh()

    fit = view.merton_for(expiry)

    rows = model_vs_market(
        chain,
        expiry,
        iv=iv,
        risk_free_rate=view.rate,
        dividend_yield=view.dividend(expiry),
        exercise=view.exercise,  # type: ignore[arg-type]
    )
    visible = set(view.visible_strikes())
    rows = [r for r in rows if r.strike in visible]

    card_title(
        tr("Il modello con una sola volatilità, contro il mercato"),
        "compare_arrows",
        subtitle=tr(
            "Il modello prezza ogni strike con la stessa IV; il mercato no. "
            "Lo scarto, strike per strike, è il sorriso della volatilità."
        ),
    )
    with ui.row().classes("w-full items-end gap-x-6 gap-y-2 flex-wrap"):
        with ui.column().classes("gap-0 grow min-w-[240px]"):
            ui.label(
                tr(
                    "IV del modello: {iv} (ATM di mercato: {atm})",
                    iv=format_percent(iv, 1),
                    atm=format_percent(atm, 1),
                )
            ).classes("text-xs t-muted")
            throttled_slider(
                minimum=5, maximum=150, step=0.5, value=round(iv * 100, 1), on_value=set_iv
            ).classes("w-full")
        ui.button(tr("IV ATM"), icon="restart_alt", on_click=reset_iv).props(
            "flat dense no-caps color=primary"
        ).classes("text-xs")
        ui.number(
            tr("Tasso"),
            value=round(view.rate * 100, 2),
            step=0.25,
            format="%.2f",
            on_change=lambda e: set_rate(e.value),
        ).props("dense outlined suffix=%").classes("w-[110px]")
        ui.number(
            tr("Dividendo"),
            value=round(view.dividend(expiry) * 100, 2),
            step=0.25,
            format="%.2f",
            on_change=lambda e: set_dividend(e.value),
        ).props("dense outlined suffix=%").classes("w-[110px]").tooltip(
            tr("Rendimento implicito per questa scadenza, ricavato dalla catena")
        )
        ui.toggle(
            {"american": tr("Americana"), "european": tr("Europea")},
            value=view.exercise,
            on_change=lambda e: set_exercise(e.value),
        ).props("dense no-caps unelevated toggle-color=primary").classes("sim-seg")
        manual = (view.manual_rate, view.manual_dividend, view.manual_exercise)
        if any(v is not None for v in manual):
            ui.button(
                tr("Valori del mercato"), icon="restart_alt", on_click=use_market_values
            ).props("flat dense no-caps color=primary").classes("text-xs")

    c = chart_palette()
    with ui.row().classes("w-full gap-4 no-wrap max-xl:flex-wrap mt-2"):
        with ui.column().classes("grow basis-0 min-w-[300px] gap-1"):
            ui.label(tr("Volatilità implicita per strike")).classes("text-sm font-semibold t-text")
            ui.echart(_smile_option(rows, chain.spot, iv, c, fit)).classes("w-full h-[300px]")
        with ui.column().classes("grow basis-0 min-w-[300px] gap-1"):
            ui.label(tr("Mercato meno modello ($ per azione)")).classes(
                "text-sm font-semibold t-text"
            )
            ui.echart(_gap_option(rows, chain.spot, c)).classes("w-full h-[300px]")

    _merton_block(view, fit, calibrate)
    _comparison_table(rows, chain.spot)
    ui.label(
        tr(
            "* Scarto = prezzo di mercato meno prezzo del modello. Rosso: il mercato "
            "chiede di più; verde: di meno. OI = interesse aperto, cioè quanti "
            "contratti esistono su quell'opzione."
        )
    ).classes(FAINT + " mt-1")

    ui.label(
        tr(
            "Tasso e dividendo non sono inventati: vengono dalla put-call parity. Una call "
            "comprata e una put venduta allo stesso strike equivalgono a possedere il "
            "titolo a termine, quindi C − P rivela il forward. Dall'S&P 500, che ha "
            "opzioni europee, si ricava il tasso; dal forward di ogni titolo il suo "
            "rendimento implicito. Con valori giusti, call e put allo stesso strike "
            "hanno la stessa IV: la casella «Verifica call/put» misura quanto ci si "
            "avvicina."
        )
    ).classes(FAINT + " mt-2")
    ui.label(
        tr(
            "Come leggerlo. Se il modello avesse ragione, la IV di mercato sarebbe una "
            "linea piatta e le barre sarebbero tutte a zero. Sulle azioni di solito le "
            "put molto fuori dal denaro (strike bassi) costano più del modello: il "
            "mercato paga una protezione contro i crolli che la lognormale considera "
            "quasi impossibili. Barre positive = il mercato chiede più del modello."
        )
    ).classes(FAINT + " mt-2")


def _merton_block(view: MarketView, fit: MertonFit | None, calibrate: Any) -> None:
    """Merton jumps: the calibrate button, then what the market is pricing in."""
    with ui.column().classes("w-full gap-3 mt-5 pt-5 sim-divider"):
        card_title(
            tr("Salti di Merton"),
            "bolt",
            tone="amber",
            subtitle=tr(
                "Un modello con crolli improvvisi: spiega le put care che Black-Scholes "
                "non riesce a spiegare."
            ),
        )
        if fit is None:
            ui.label(
                tr(
                    "Cerca quanti salti all'anno, e di che grandezza, rendono i prezzi del "
                    "modello uguali a quelli di mercato su questa scadenza. Usa le opzioni "
                    "fuori dal denaro, le più scambiate."
                )
            ).classes(FAINT)
            ui.button(
                tr("Calibrazione in corso…") if view.calibrating else tr("Calibra i salti"),
                icon="auto_graph",
                on_click=calibrate,
            ).props("unelevated no-caps" + (" loading" if view.calibrating else "")).classes(
                "self-start"
            )
            return

        jump = fit.jumps.expected_jump
        sign = "−" if jump < 0 else "+"
        with ui.element("div").classes("w-full grid gap-2 grid-cols-2 md:grid-cols-3"):
            stat(
                tr("Salti attesi all'anno"),
                format_number(fit.jumps.intensity, 2),
                sub=tr("quanti ne prezza il mercato"),
                icon="bolt",
            )
            stat(
                tr("Salto medio"),
                f"{sign}{format_percent(abs(jump), 1)}",
                tone="loss" if jump < 0 else "profit",
                sub=tr("negativo = crollo"),
                icon="south_east" if jump < 0 else "north_east",
            )
            stat(
                tr("Variabilità dei salti"),
                format_percent(fit.jumps.vol, 1),
                sub=tr("quanto cambiano da un salto all'altro"),
                icon="scatter_plot",
            )
            stat(
                tr("Volatilità senza salti"),
                format_percent(fit.sigma, 1),
                sub=tr("il movimento continuo di tutti i giorni"),
                icon="waves",
            )
            stat(
                tr("Errore Black-Scholes"),
                tr("{value} punti", value=format_number(fit.bsm_rmse, 2)),
                tone="loss",
                sub=tr("con la migliore volatilità unica"),
                icon="straighten",
            )
            stat(
                tr("Errore Merton"),
                tr("{value} punti", value=format_number(fit.rmse, 2)),
                tone="profit",
                sub=tr("scarto medio dalla IV di mercato"),
                icon="straighten",
            )
        ui.label(
            tr(
                "Come leggerlo: su questa scadenza il mercato prezza in media {count} salti "
                "all'anno, di circa {size} ciascuno. Con i salti l'errore sulla volatilità "
                "implicita scende da {bsm} a {merton} punti: la curva «Merton» nel grafico "
                "segue il sorriso, la linea del modello a volatilità unica no.",
                count=format_number(fit.jumps.intensity, 2),
                size=f"{sign}{format_percent(abs(jump), 1)}",
                bsm=format_number(fit.bsm_rmse, 2),
                merton=format_number(fit.rmse, 2),
            )
        ).classes("text-sm t-text2")
        if view.exercise == "american":
            ui.label(
                tr(
                    "Le opzioni su azioni sono americane: la formula di Merton è per le "
                    "europee, quindi qui usa solo le opzioni fuori dal denaro, dove "
                    "l'esercizio anticipato vale poco."
                )
            ).classes(FAINT)
        ui.button(
            tr("Calibrazione in corso…") if view.calibrating else tr("Ricalibra"),
            icon="refresh",
            on_click=calibrate,
        ).props(
            "flat dense no-caps color=primary" + (" loading" if view.calibrating else "")
        ).classes("self-start text-xs")


def _comparison_table(rows: list[ModelRow], spot: float) -> None:
    def gap_cell(market: float | None, model: float) -> None:
        if market is None:
            ui.label("—").classes("w-[72px] text-right")
            return
        gap = market - model
        ui.label(format_signed_money(gap, "")).classes("w-[72px] text-right font-semibold").style(
            f"color: {COLOR_LOSS if gap > 0 else COLOR_PROFIT}"
        )

    with ui.column().classes("w-full gap-0 overflow-x-auto mt-3"):
        with ui.row().classes("min-w-[640px] w-full no-wrap gap-1 sim-thead pb-2 px-1"):
            for text in ["Call merc.", "Call mod.", "Scarto*"]:
                ui.label(tr(text)).classes("w-[72px] text-right")
            ui.label(tr("Strike")).classes("grow text-center")
            for text in ["Put merc.", "Put mod.", "Scarto*"]:
                ui.label(tr(text)).classes("w-[72px] text-right")
        for row in rows:
            near = abs(row.strike - spot) <= spot * 0.01
            with ui.row().classes(
                "min-w-[640px] w-full no-wrap gap-1 text-[13px] t-text2 t-num py-1 px-1 "
                "sim-divider" + (" sim-itm" if near else "")
            ):
                ui.label(price_text(row.call_market)).classes("w-[72px] text-right")
                ui.label(format_number(row.call_model, 2)).classes("w-[72px] text-right")
                gap_cell(row.call_market, row.call_model)
                ui.label(format_number(row.strike, 2)).classes(
                    "grow text-center font-semibold t-text"
                )
                ui.label(price_text(row.put_market)).classes("w-[72px] text-right")
                ui.label(format_number(row.put_model, 2)).classes("w-[72px] text-right")
                gap_cell(row.put_market, row.put_model)


def _axis(c: dict[str, str]) -> dict[str, Any]:
    return {
        "axisLabel": {"color": c["axis"], "fontSize": 11},
        "axisLine": {"lineStyle": {"color": c["grid"]}},
        "splitLine": {"lineStyle": {"color": c["grid"]}},
    }


def _base(c: dict[str, str]) -> dict[str, Any]:
    return {
        "backgroundColor": "transparent",
        "animation": False,
        "textStyle": {"fontFamily": c["font"]},
        "grid": {"left": 52, "right": 16, "top": 36, "bottom": 30},
        "legend": {"top": 4, "right": 8, "textStyle": {"color": c["axis"], "fontSize": 11}},
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": c["tooltip_bg"],
            "borderColor": c["tooltip_border"],
            "textStyle": {"color": c["expiry"], "fontSize": 12},
        },
    }


def _spot_line(spot: float, c: dict[str, str]) -> dict[str, Any]:
    return {
        "silent": True,
        "symbol": "none",
        "data": [{"xAxis": spot}],
        "lineStyle": {"color": c["spot"], "type": "solid", "width": 1.2},
        "label": {"formatter": tr("prezzo"), "color": c["spot"], "fontSize": 10},
    }


def _smile_option(
    rows: list[ModelRow],
    spot: float,
    iv: float,
    c: dict[str, str],
    fit: MertonFit | None = None,
) -> dict[str, Any]:
    def points(attr: str) -> list[list[float]]:
        return [
            [r.strike, round(getattr(r, attr) * 100, 2)]
            for r in rows
            if getattr(r, attr) is not None
        ]

    strikes = [r.strike for r in rows] or [spot]
    merton: list[dict[str, Any]] = []
    if fit is not None:
        low, high = min(strikes), max(strikes)
        merton.append(
            {
                "name": tr("Merton"),
                "type": "line",
                "data": [
                    [k, round(v * 100, 2)]
                    for k, v in zip(fit.strikes, fit.model_iv, strict=True)
                    if low <= k <= high
                ],
                "showSymbol": False,
                "smooth": True,
                "lineStyle": {"color": c["today"], "width": 2.6},
                "itemStyle": {"color": c["today"]},
            }
        )
    return {
        **_base(c),
        "xAxis": {"type": "value", "min": min(strikes), "max": max(strikes), **_axis(c)},
        "yAxis": {
            "type": "value",
            "scale": True,
            "axisLabel": {"color": c["axis"], "fontSize": 11, "formatter": "{value}%"},
            "splitLine": {"lineStyle": {"color": c["grid"]}},
        },
        "series": [
            {
                "name": tr("IV call"),
                "type": "line",
                "data": points("call_iv"),
                "symbolSize": 5,
                "lineStyle": {"color": c["profit"], "width": 2},
                "itemStyle": {"color": c["profit"]},
                "markLine": _spot_line(spot, c),
            },
            {
                "name": tr("IV put"),
                "type": "line",
                "data": points("put_iv"),
                "symbolSize": 5,
                "lineStyle": {"color": c["loss"], "width": 2},
                "itemStyle": {"color": c["loss"]},
            },
            {
                "name": tr("Modello"),
                "type": "line",
                "data": [[min(strikes), iv * 100], [max(strikes), iv * 100]],
                "showSymbol": False,
                "lineStyle": {"color": c["forward"], "width": 2, "type": "dashed"},
                "itemStyle": {"color": c["forward"]},
            },
            *merton,
        ],
    }


def _gap_option(rows: list[ModelRow], spot: float, c: dict[str, str]) -> dict[str, Any]:
    def gaps(market: str, model: str) -> list[list[float]]:
        return [
            [r.strike, round(getattr(r, market) - getattr(r, model), 3)]
            for r in rows
            if getattr(r, market) is not None
        ]

    strikes = [r.strike for r in rows] or [spot]
    width = max(4, 300 // max(len(rows), 1) // 3)
    return {
        **_base(c),
        "xAxis": {"type": "value", "min": min(strikes), "max": max(strikes), **_axis(c)},
        "yAxis": {"type": "value", **_axis(c)},
        "series": [
            {
                "name": tr("Call"),
                "type": "bar",
                "data": gaps("call_market", "call_model"),
                "barWidth": width,
                "itemStyle": {"color": c["profit"], "borderRadius": 2},
                "markLine": _spot_line(spot, c),
            },
            {
                "name": tr("Put"),
                "type": "bar",
                "data": gaps("put_market", "put_model"),
                "barWidth": width,
                "itemStyle": {"color": c["loss"], "borderRadius": 2},
            },
        ],
    }
