"""La pagina del portafoglio virtuale.

--- COSA FA QUESTO FILE ---
Definisce l'indirizzo `/portafoglio`: le posizioni aperte ai prezzi veri dalla
pagina «Opzioni reali», con il loro valore aggiornato, l'andamento giorno per
giorno, e il confronto fra ciò che il modello prevedeva e ciò che è successo.

I calcoli e il salvataggio stanno in `portfolio.py`; qui c'è l'interfaccia.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from typing import Any

from nicegui import run, ui

from .. import auth, portfolio, session
from ..formatting import (
    format_date,
    format_money,
    format_number,
    format_percent,
    format_short_date,
    format_signed_money,
    format_timestamp,
)
from ..i18n import tr, trn
from ..layout import page_frame
from ..market_data import BasketLeg, Chain, MarketDataError, fetch_chain, position_from_basket
from ..portfolio import PaperPosition
from ..theme import chart_palette
from ..tickers import CATALOG, CATEGORY_TONES, display_symbol
from ..widgets import CARD, COLOR_LOSS, COLOR_PROFIT, FAINT, card_title, stat

STALE_MINUTES = 15
PAUSE_BETWEEN_REQUESTS = 1.0  # secondi: CBOE mette in pausa chi chiede troppo


def _tone(ticker: str) -> str:
    for category, items in CATALOG.items():
        if any(symbol == ticker for symbol, _ in items):
            return CATEGORY_TONES.get(category, "accent")
    return "accent"


def _fetch_many(tickers: list[str]) -> tuple[dict[str, Chain], list[str]]:
    """Scarica le catene una alla volta, con una pausa fra l'una e l'altra."""
    chains: dict[str, Chain] = {}
    errors: list[str] = []
    for index, ticker in enumerate(tickers):
        if index:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
        try:
            chains[ticker] = fetch_chain(ticker)
        except MarketDataError as error:
            errors.append(f"{display_symbol(ticker)}: {error}")
    return chains, errors


def _minutes_since(iso: str | None) -> float:
    if not iso:
        return float("inf")
    try:
        return (datetime.now(UTC) - datetime.fromisoformat(iso)).total_seconds() / 60
    except ValueError:
        return float("inf")


def _pl_color(value: float | None) -> str:
    return COLOR_PROFIT if (value or 0.0) >= 0 else COLOR_LOSS


@ui.page("/portafoglio")
def portfolio_page() -> None:
    if not auth.require_login():
        return
    username = auth.current_username()
    if username is None:
        return
    session.touch(username)
    session.STATS.page_views += 1
    status = {"busy": False}
    # Le operazioni lente ridisegnano la pagina mentre aspettano la rete, e il
    # pulsante che le ha avviate sparisce: messaggi e navigazione si agganciano
    # quindi alla pagina, che resta.
    root = ui.context.client.layout

    def notify(message: str, **kwargs: Any) -> None:
        with root:
            ui.notify(message, **kwargs)

    def go_to(path: str) -> None:
        with root:
            ui.navigate.to(path)

    async def refresh_prices(*, quiet: bool = False) -> None:
        tickers = portfolio.tickers_to_refresh(username)
        if not tickers or status["busy"]:
            return
        status["busy"] = True
        content.refresh()
        result = await run.io_bound(_fetch_many, tickers)
        status["busy"] = False
        if result is None:
            return
        chains, errors = result
        count = portfolio.refresh(username, chains)
        for error in errors:
            notify(error, type="warning", multi_line=True)
        if not quiet:
            notify(tr("Prezzi aggiornati per {count} posizioni", count=count), type="positive")
        content.refresh()

    async def close(position: PaperPosition) -> None:
        status["busy"] = True
        content.refresh()
        try:
            chain = await run.io_bound(fetch_chain, position.ticker)
        except MarketDataError as error:
            notify(str(error), type="negative")
            chain = None
        status["busy"] = False
        if chain is not None:
            closed = portfolio.close_position(username, position.position_id, chain)
            notify(
                tr(
                    "Chiusa {display_ticker}: {signed_money}",
                    display_ticker=closed.display_ticker,
                    signed_money=format_signed_money(closed.pl or 0.0),
                ),
                type="positive" if (closed.pl or 0.0) >= 0 else "warning",
            )
        content.refresh()

    async def open_in_simulator(position: PaperPosition) -> None:
        try:
            chain = await run.io_bound(fetch_chain, position.ticker)
        except MarketDataError as error:
            notify(str(error), type="negative")
            return
        if chain is None:
            return
        basket = [
            BasketLeg(
                right=leg.right,  # type: ignore[arg-type]
                side=leg.side,  # type: ignore[arg-type]
                strike=leg.strike,
                qty=leg.contracts,
                premium=leg.entry_price,
                iv=None,
            )
            for leg in position.legs
        ]
        state = position_from_basket(
            chain,
            position.expiry_date,
            basket,
            risk_free_rate=position.rate,
            dividend_yield=position.dividend,
            exercise=position.exercise,  # type: ignore[arg-type]
        )
        session.replace_position(state)
        go_to("/")

    def remove(position: PaperPosition) -> None:
        portfolio.delete(username, position.position_id)
        ui.notify(tr("Eliminata {display_ticker}", display_ticker=position.display_ticker))
        content.refresh()

    def confirm_close(position: PaperPosition) -> None:
        with ui.dialog() as dialog, ui.card().classes("sim-card w-[420px] max-w-full gap-3"):
            card_title(
                tr("Chiudere {display_ticker}?", display_ticker=position.display_ticker),
                "logout",
                tone="red",
            )
            ui.label(
                tr(
                    "Si chiude ai prezzi reali di adesso: le opzioni comprate si vendono al "
                    "prezzo denaro, quelle vendute si ricomprano al prezzo lettera. È il costo "
                    "vero dell'uscita, di solito un po' peggiore del valore «a metà»."
                )
            ).classes("text-sm t-muted")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(tr("Annulla"), on_click=dialog.close).props("flat no-caps").classes(
                    "t-muted"
                )

                async def go() -> None:
                    dialog.close()
                    await close(position)

                ui.button(tr("Chiudi la posizione"), icon="logout", on_click=go).props(
                    "unelevated no-caps color=negative"
                )
        dialog.open()

    with page_frame(
        "/portafoglio",
        subtitle=tr(
            "Posizioni aperte per finta ai prezzi veri: torna nei prossimi giorni e "
            "scopri se il modello aveva ragione."
        ),
    ):

        @ui.refreshable
        def content() -> None:
            positions = portfolio.list_for(username)
            open_positions = [p for p in positions if p.status == "open"]
            closed_positions = [p for p in positions if p.status == "closed"]

            _summary(open_positions, closed_positions, status["busy"], lambda: refresh_prices())
            _calibration_card(positions)

            if not positions:
                with ui.card().classes(CARD):
                    card_title(tr("Il portafoglio è vuoto"), "account_balance_wallet")
                    ui.label(
                        tr(
                            "Vai su «Opzioni reali», scegli un titolo e una o più opzioni, poi "
                            "premi «Apri nel portafoglio». Il simulatore ricorda i prezzi che "
                            "avresti pagato davvero e la previsione del modello in quel momento."
                        )
                    ).classes("text-sm t-muted")
                    ui.button(
                        tr("Vai alle opzioni reali"),
                        icon="travel_explore",
                        on_click=lambda: ui.navigate.to("/mercato"),
                    ).props("unelevated no-caps").classes("self-start mt-2")
                return

            if open_positions:
                ui.label(tr("Posizioni aperte")).classes("sim-card-title mt-2")
                with ui.element("div").classes("w-full grid gap-4 grid-cols-1 xl:grid-cols-2"):
                    for position in open_positions:
                        _open_card(position, confirm_close, open_in_simulator, remove)
            if closed_positions:
                _closed_table(closed_positions, remove)

        content()

    # Se i prezzi sono vecchi, si aggiornano da soli all'apertura della pagina.
    stale = [
        p
        for p in portfolio.list_for(username)
        if p.status == "open" and _minutes_since(p.last_update) > STALE_MINUTES
    ]
    if stale:
        ui.timer(0.3, lambda: refresh_prices(quiet=True), once=True)


# ---------------------------------------------------------------------------
# Riepilogo in alto
# ---------------------------------------------------------------------------


def _summary(
    open_positions: list[PaperPosition],
    closed_positions: list[PaperPosition],
    busy: bool,
    on_refresh: Any,
) -> None:
    with ui.card().classes(CARD):
        last = max((p.last_update or "" for p in open_positions), default="")
        card_title(
            tr("Il tuo portafoglio virtuale"),
            "account_balance_wallet",
            subtitle=(
                tr(
                    "Prezzi aggiornati al {timestamp} · dati CBOE in ritardo di 15 minuti",
                    timestamp=format_timestamp(last),
                )
                if last
                else tr("Nessuna posizione aperta")
            ),
            action=(tr("Aggiorna prezzi"), "refresh", on_refresh) if open_positions else None,
        )
        if busy:
            with ui.row().classes("items-center gap-2 -mt-1 mb-2"):
                ui.spinner(size="sm").classes("t-accent")
                ui.label(tr("Scarico i prezzi, un titolo alla volta…")).classes("text-xs t-muted")
        open_pl = sum(p.pl or 0.0 for p in open_positions)
        realized = sum(p.pl or 0.0 for p in closed_positions)
        with ui.element("div").classes("w-full grid gap-2 grid-cols-2 md:grid-cols-4"):
            stat(tr("Posizioni aperte"), str(len(open_positions)), icon="work")
            stat(
                tr("Valore attuale"),
                format_money(sum(p.last_value or 0.0 for p in open_positions)),
                sub=tr("al prezzo medio fra denaro e lettera"),
                icon="account_balance",
            )
            stat(
                tr("Guadagno / perdita aperti"),
                format_signed_money(open_pl),
                tone="profit" if open_pl >= 0 else "loss",
                sub=tr("non ancora realizzati"),
                icon="trending_up" if open_pl >= 0 else "trending_down",
            )
            stat(
                tr("Realizzato"),
                format_signed_money(realized),
                tone="profit" if realized >= 0 else "loss",
                sub=trn("{n} posizione chiusa", "{n} posizioni chiuse", len(closed_positions)),
                icon="savings",
            )


def _calibration_card(positions: list[PaperPosition]) -> None:
    result = portfolio.calibration(positions)
    with ui.card().classes(CARD):
        card_title(
            tr("Le tue previsioni contro la realtà"),
            "fact_check",
            tone="violet",
            subtitle=tr(
                "Quanto spesso il modello ci prende: la probabilità che ti dava "
                "all'apertura contro come sono finite davvero le posizioni chiuse."
            ),
        )
        if result is None:
            ui.label(
                tr(
                    "Appare quando avrai chiuso almeno una posizione (o una sarà scaduta). "
                    "Più posizioni chiudi, più il confronto diventa significativo."
                )
            ).classes(FAINT)
            return
        with ui.element("div").classes("w-full grid gap-2 grid-cols-1 md:grid-cols-3"):
            stat(
                tr("Il modello prevedeva"),
                format_percent(result.average_probability, 0),
                sub=tr("probabilità media di profitto all'apertura"),
                icon="casino",
            )
            stat(
                tr("È successo"),
                format_percent(result.win_rate, 0),
                tone="profit" if result.win_rate >= result.average_probability else "loss",
                sub=tr("{wins} in guadagno su {closed}", wins=result.wins, closed=result.closed),
                icon="flag",
            )
            stat(
                tr("Risultato complessivo"),
                format_signed_money(result.realized_pl),
                tone="profit" if result.realized_pl >= 0 else "loss",
                icon="savings",
            )
        ui.label(
            tr(
                "Con poche posizioni il caso pesa molto: servono decine di operazioni prima "
                "che la percentuale reale si avvicini a quella prevista. E una probabilità "
                "di profitto alta non basta: conta anche quanto si guadagna quando va bene "
                "e quanto si perde quando va male."
            )
            if result.closed < 20
            else tr(
                "Se la percentuale reale resta lontana da quella prevista, il modello "
                "(volatilità costante, nessun salto di prezzo) non descrive bene i titoli che "
                "scegli: è il sorriso di volatilità che lavora."
            )
        ).classes(FAINT + " mt-2")


# ---------------------------------------------------------------------------
# Posizioni aperte
# ---------------------------------------------------------------------------


def _change(before: float, after: float | None, *, percent: bool = False) -> str:
    if after is None:
        return "—"
    if percent:
        return f"{format_percent(before, 1)} → {format_percent(after, 1)}"
    move = after / before - 1 if before else 0.0
    return (
        f"{format_number(before, 2)} → {format_number(after, 2)} "
        f"({'+' if move >= 0 else ''}{format_percent(move, 1)})"
    )


def _kv(label: str, value: str) -> None:
    with ui.column().classes("gap-0 min-w-[120px]"):
        ui.label(label).classes("sim-stat-label")
        ui.label(value).classes("text-sm t-text t-num")


def _sparkline(position: PaperPosition) -> None:
    points = position.snapshots
    if len(points) < 2:
        ui.label(tr("Il grafico dell'andamento compare dal secondo giorno: torna domani.")).classes(
            FAINT
        )
        return
    c = chart_palette()
    values = [round(s.value - position.entry_cost, 2) for s in points]
    color = c["profit"] if values[-1] >= 0 else c["loss"]
    ui.echart(
        {
            "backgroundColor": "transparent",
            "animation": False,
            "grid": {"left": 48, "right": 8, "top": 8, "bottom": 22},
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": c["tooltip_bg"],
                "borderColor": c["tooltip_border"],
                "textStyle": {"color": c["expiry"], "fontSize": 12},
            },
            "xAxis": {
                "type": "category",
                "data": [format_short_date(date.fromisoformat(s.day)) for s in points],
                "axisLabel": {"color": c["axis"], "fontSize": 10},
                "axisLine": {"lineStyle": {"color": c["grid"]}},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {"color": c["axis"], "fontSize": 10},
                "splitLine": {"lineStyle": {"color": c["grid"]}},
            },
            "series": [
                {
                    "name": tr("Guadagno / perdita $"),
                    "type": "line",
                    "data": values,
                    "smooth": True,
                    "symbolSize": 5,
                    "lineStyle": {"color": color, "width": 2},
                    "itemStyle": {"color": color},
                    "areaStyle": {"color": color, "opacity": 0.12},
                    "markLine": {
                        "silent": True,
                        "symbol": "none",
                        "data": [{"yAxis": 0}],
                        "lineStyle": {"color": c["axis"], "type": "dashed"},
                        "label": {"show": False},
                    },
                }
            ],
        }
    ).classes("w-full h-[150px]")


def _open_card(position: PaperPosition, on_close: Any, on_simulator: Any, on_delete: Any) -> None:
    days_left = (position.expiry_date - date.today()).days
    pl = position.pl
    forecast = position.forecast
    with ui.card().classes(CARD + " gap-3"):
        with ui.row().classes("w-full items-start gap-3 no-wrap"):
            ui.label(position.display_ticker).classes(
                f"sim-tone-badge tone-{_tone(position.ticker)} text-sm mt-0.5"
            )
            with ui.column().classes("gap-0 grow min-w-0"):
                ui.label(position.name).classes("sim-card-title truncate")
                ui.label(position.describe()).classes("text-xs t-muted")
                ui.label(
                    tr(
                        "Aperta il {timestamp} · scade il {strftime} ({days_left} gg)",
                        timestamp=format_timestamp(position.opened_at),
                        strftime=format_date(position.expiry_date),
                        days_left=days_left,
                    )
                ).classes("text-[11px] t-faint")
            with ui.column().classes("gap-0 items-end shrink-0"):
                ui.label(format_signed_money(pl) if pl is not None else "—").classes(
                    "sim-stat-value"
                ).style(f"color: {_pl_color(pl)}")
                pct = position.pl_pct
                ui.label(
                    tr(
                        "{sign}{pct} sul premio",
                        sign="+" if (pct or 0) >= 0 else "",
                        pct=format_percent(pct, 1),
                    )
                    if pct is not None
                    else ""
                ).classes("text-[11px] t-muted")

        with ui.row().classes("w-full gap-x-6 gap-y-2 flex-wrap"):
            debit = position.entry_cost >= 0
            _kv(
                tr("Pagato") if debit else tr("Incassato"),
                format_money(abs(position.entry_cost)),
            )
            _kv(tr("Vale ora"), format_money(position.last_value or 0.0))
            _kv(tr("Prezzo del titolo"), _change(position.entry_spot, position.last_spot))
            _kv(tr("Volatilità ATM"), _change(position.entry_iv, position.last_iv, percent=True))

        with ui.row().classes("w-full gap-x-6 gap-y-2 flex-wrap sim-divider pt-2"):
            _kv(
                tr("Il modello dava"),
                tr(
                    "{prob_profit} di profitto", prob_profit=format_percent(forecast.prob_profit, 0)
                ),
            )
            _kv(
                tr("Break-even"),
                "  ·  ".join(format_number(b, 2) for b in forecast.break_evens) or tr("nessuno"),
            )
            _kv(
                tr("Guadagno massimo"),
                format_money(forecast.max_profit)
                if forecast.max_profit is not None
                else tr("illimitato"),
            )
            _kv(
                tr("Perdita massima"),
                format_money(abs(forecast.max_loss))
                if forecast.max_loss is not None
                else tr("illimitata"),
            )
        if position.note:
            ui.label(tr("La tua previsione: «{note}»", note=position.note)).classes(
                "text-xs t-text2 italic"
            )

        if len(position.snapshots) <= 1 and (pl or 0.0) < 0:
            ui.label(
                tr(
                    "Appena aperta, la posizione vale già un po' meno di quanto pagato: il "
                    "valore si misura «a metà» fra denaro e lettera, mentre tu hai comprato "
                    "alla lettera e venduto al denaro. È lo spread, il costo nascosto di "
                    "ogni operazione."
                )
            ).classes(FAINT)
        _sparkline(position)

        with ui.row().classes("w-full gap-2 justify-end"):
            ui.button(
                tr("Apri nel simulatore"),
                icon="candlestick_chart",
                on_click=lambda _, p=position: on_simulator(p),
            ).props("flat dense no-caps color=primary").classes("text-xs")
            ui.button(
                tr("Elimina"), icon="delete_outline", on_click=lambda _, p=position: on_delete(p)
            ).props("flat dense no-caps").classes("text-xs t-muted")
            ui.button(
                tr("Chiudi"), icon="logout", on_click=lambda _, p=position: on_close(p)
            ).props("unelevated dense no-caps color=primary").classes("text-xs px-3")


# ---------------------------------------------------------------------------
# Posizioni chiuse
# ---------------------------------------------------------------------------


def _closed_table(positions: list[PaperPosition], on_delete: Any) -> None:
    with ui.card().classes(CARD):
        card_title(tr("Posizioni chiuse"), "inventory_2", tone="blue")
        with ui.column().classes("w-full gap-0 overflow-x-auto"):
            with ui.row().classes("min-w-[720px] w-full gap-2 no-wrap sim-thead px-1 pb-2"):
                ui.label(tr("Titolo")).classes("w-16")
                ui.label(tr("Posizione")).classes("grow")
                ui.label(tr("Chiusa il")).classes("w-36")
                ui.label(tr("Prevista")).classes("w-20 text-right")
                ui.label(tr("Risultato")).classes("w-28 text-right")
                ui.label("").classes("w-8")
            for position in positions:
                pl = position.pl or 0.0
                with ui.row().classes(
                    "min-w-[720px] w-full gap-2 no-wrap items-center text-sm t-text2 t-num "
                    "py-2 sim-divider px-1"
                ):
                    ui.label(position.display_ticker).classes(
                        f"w-16 sim-tone-badge tone-{_tone(position.ticker)}"
                    )
                    with ui.column().classes("grow gap-0 min-w-0"):
                        ui.label(position.describe()).classes("truncate")
                        if position.settled_at_expiry:
                            ui.label(
                                tr(
                                    "regolata a scadenza al valore intrinseco (prezzo del giorno "
                                    "dell'aggiornamento)"
                                )
                            ).classes("text-[11px] t-faint")
                    ui.label(format_timestamp(position.closed_at or "")).classes(
                        "w-36 text-xs t-muted"
                    )
                    ui.label(format_percent(position.forecast.prob_profit, 0)).classes(
                        "w-20 text-right t-muted"
                    ).tooltip(tr("Probabilità di profitto che dava il modello all'apertura"))
                    with ui.row().classes("w-28 justify-end items-center gap-1 no-wrap"):
                        ui.icon("check_circle" if pl > 0 else "cancel", size="16px").style(
                            f"color: {_pl_color(pl)}"
                        )
                        ui.label(format_signed_money(pl)).classes("font-semibold").style(
                            f"color: {_pl_color(pl)}"
                        )
                    ui.button(
                        icon="delete_outline", on_click=lambda _, p=position: on_delete(p)
                    ).props("flat dense round size=sm").classes("w-8 t-faint").tooltip(
                        tr("Elimina")
                    )
