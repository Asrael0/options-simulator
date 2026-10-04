"""The real options page: ``/market``.

The user types a US stock (AAPL, SPY…), the simulator downloads every listed
option from CBOE and shows them in three tabs, one module each:

  «Chain»            — ``chain.py``: the classic broker table.
  «Model vs market»  — ``comparison.py``: a single volatility against real
                       prices, i.e. the volatility smile.
  «Volatility»       — ``volatility_tab.py``: implied against historical.

The «Your picks» card is in ``basket.py``, the page state in ``view.py``. This
module is the page itself: stock search, data loading (chain, rate and dividend,
check, history) and layout. Network and calculation work lives in
``market_data.py``, ``carry.py`` and ``volatility.py``.
"""

from __future__ import annotations

from datetime import date

from nicegui import run, ui

from ....pricing import Right
from ... import auth, session
from ...carry import (
    carry_for,
    fetch_rate,
    parity_check,
)
from ...formatting import format_date, format_money, format_number, format_percent
from ...i18n import tr
from ...layout import page_frame
from ...market_data import (
    SOURCE_NAME,
    BasketLeg,
    MarketDataError,
    fetch_chain,
)
from ...tickers import CATALOG, CATEGORY_TONES, POPULAR, company_name, display_symbol
from ...volatility import volatility_report
from ...widgets import (
    CARD,
    FAINT,
    card_title,
    stat,
    ticker_search,
)
from .basket import render_basket
from .chain import render_chain
from .comparison import render_comparison
from .view import RANGES, MarketView, expiry_label, price_text, quoted_at
from .volatility_tab import render_volatility


@ui.page("/market")
def market_page() -> None:
    if not auth.require_login():
        return
    info = session.touch(auth.current_username())
    session.STATS.page_views += 1
    view = MarketView(info)

    # While loading, the page redraws and the pressed button disappears:
    # notifications are therefore attached to the page layout, which stays.
    root = ui.context.client.layout

    async def load(ticker: str) -> None:
        view.loading = True
        header.refresh()
        try:
            chain = await run.io_bound(fetch_chain, ticker)
        except MarketDataError as error:
            with root:
                ui.notify(str(error), type="negative", multi_line=True)
            view.loading = False
            header.refresh()
            return
        if chain is None:  # the server is shutting down
            return
        if chain.ticker != info.market_ticker:
            info.market_expiry = None
            info.basket = []
        view.chain = chain
        info.market_ticker = chain.ticker
        view.model_iv = None
        view.reset_carry()
        view.merton = view.merton_key = None
        rate = await run.io_bound(fetch_rate)
        if rate is None:
            return
        view.carry = carry_for(chain, rate)
        view.check = None
        view.loading = False
        view.checking = True
        refresh_all()
        # The check solves hundreds of implied volatilities: run it after the
        # chain is on screen, not before.
        view.check = await run.io_bound(parity_check, chain, view.carry)
        view.checking = False
        header.refresh()
        # Price history last, for the «Volatility» tab.
        view.vol, view.vol_error, view.vol_loading = None, None, True
        volatility_tab.refresh()
        try:
            view.vol = await run.io_bound(volatility_report, chain.ticker, chain.iv30)
        except MarketDataError as error:
            view.vol_error = str(error)
        view.vol_loading = False
        volatility_tab.refresh()

    def refresh_all() -> None:
        header.refresh()
        body.refresh()
        basket_card.refresh()

    def set_expiry(value: date) -> None:
        if info.basket and value != info.market_expiry:
            info.basket.clear()
            ui.notify(tr("Selezione svuotata: le gambe devono avere la stessa scadenza."))
        info.market_expiry = value
        view.model_iv = None
        body.refresh()
        basket_card.refresh()

    def set_range(value: str) -> None:
        view.range_key = value
        body.refresh()

    # -- picking an option ----------------------------------------------------

    def ask_side(right: Right, strike: float) -> None:
        view.pending = (right, strike)
        side_dialog_content.refresh()
        side_dialog.open()

    def add_leg(side: str) -> None:
        side_dialog.close()
        if view.chain is None or view.expiry is None or view.pending is None:
            return
        right, strike = view.pending
        quote = view.chain.quote(view.expiry, right, strike)
        if quote is None:
            return
        price = (quote.ask if side == "long" else quote.bid) or quote.mid
        if not price:
            ui.notify(tr("Questa opzione non ha un prezzo utilizzabile."), type="warning")
            return
        info.market_expiry = view.expiry
        info.basket.append(
            BasketLeg(
                right=right,
                side=side,  # type: ignore[arg-type]
                strike=strike,
                qty=1,
                premium=price,
                iv=quote.iv,
            )
        )
        basket_card.refresh()

    with ui.dialog() as side_dialog, ui.card().classes("sim-card w-[380px] max-w-full gap-3"):

        @ui.refreshable
        def side_dialog_content() -> None:
            if view.chain is None or view.expiry is None or view.pending is None:
                return
            right, strike = view.pending
            quote = view.chain.quote(view.expiry, right, strike)
            if quote is None:
                return
            card_title(
                tr("{title} {strike}", title=tr(right.title()), strike=format_number(strike, 2)),
                "add_shopping_cart",
                subtitle=tr(
                    "{display_symbol} · scadenza {strftime}",
                    display_symbol=display_symbol(view.chain.ticker),
                    strftime=format_date(view.expiry),
                ),
            )
            ui.label(
                tr(
                    "Chi compra paga il prezzo lettera, chi vende incassa il denaro: la "
                    "differenza (lo spread) è il costo nascosto di ogni operazione."
                )
            ).classes(FAINT)
            with ui.row().classes("w-full gap-2 no-wrap"):
                ui.button(
                    tr("Compra a {price_text}", price_text=price_text(quote.ask)),
                    icon="north_east",
                    on_click=lambda: add_leg("long"),
                ).props("unelevated no-caps color=positive").classes("grow").set_enabled(
                    quote.ask > 0
                )
                ui.button(
                    tr("Vendi a {price_text}", price_text=price_text(quote.bid)),
                    icon="south_east",
                    on_click=lambda: add_leg("short"),
                ).props("unelevated no-caps color=negative").classes("grow").set_enabled(
                    quote.bid > 0
                )

        side_dialog_content()

    # -- header: search and stock data -------------------------------------

    with page_frame(
        "/market",
        subtitle=tr(
            "Le opzioni quotate davvero: guardale, scegline alcune e studiale nel "
            "simulatore, o confronta il mercato con il modello."
        ),
    ):

        @ui.refreshable
        def header() -> None:
            with ui.card().classes(CARD):
                card_title(
                    tr("Carica un titolo"),
                    "travel_explore",
                    subtitle=tr(
                        "Titoli, ETF e indici USA · fonte: {source_name}",
                        source_name=tr(SOURCE_NAME),
                    ),
                )
                with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                    ticker_search(
                        label=tr("Cerca un titolo o scrivi un simbolo USA"),
                        value=display_symbol(info.market_ticker or ""),
                        on_pick=load,
                        classes="w-[360px] max-w-full",
                    ).props(f'placeholder="{tr("es. Apple, AAPL, Ferrari…")}"')
                    if view.loading:
                        ui.spinner(size="sm").classes("t-accent")
                    ui.space()
                    for quick in POPULAR:
                        ui.button(display_symbol(quick), on_click=lambda _, t=quick: load(t)).props(
                            "outline dense no-caps color=primary"
                        ).classes("text-xs px-2")

                with (
                    ui.expansion(tr("Sfoglia per categoria"), icon="category")
                    .props("dense")
                    .classes("w-full text-sm t-text2")
                ):
                    for category, items in CATALOG.items():
                        with ui.row().classes(
                            "w-full items-start gap-2 no-wrap py-1.5 sim-divider"
                        ):
                            ui.label(tr(category)).classes(
                                "w-[200px] shrink-0 text-xs t-muted pt-1"
                            )
                            with ui.row().classes("gap-1 flex-wrap"):
                                tone = CATEGORY_TONES.get(category, "accent")
                                for symbol, name in items:
                                    ui.button(
                                        display_symbol(symbol),
                                        on_click=lambda _, t=symbol: load(t),
                                    ).props("flat dense no-caps").classes(
                                        f"text-xs px-2 tone-{tone} sim-tone-text"
                                    ).tooltip(name)

                chain = view.chain
                if chain is None:
                    return
                with ui.element("div").classes("w-full grid gap-2 grid-cols-2 md:grid-cols-4 mt-3"):
                    stat(
                        tr(
                            "{display_symbol} · {name}",
                            display_symbol=display_symbol(chain.ticker),
                            name=company_name(chain.ticker) or tr("prezzo"),
                        ),
                        format_money(chain.spot),
                        icon="show_chart",
                    )
                    stat(
                        tr("Variazione del giorno"),
                        tr(
                            "{x}{change_pct}",
                            x="+" if chain.change_pct >= 0 else "",
                            change_pct=format_percent(chain.change_pct, 2),
                        ),
                        tone="profit" if chain.change_pct >= 0 else "loss",
                        icon="trending_up" if chain.change_pct >= 0 else "trending_down",
                    )
                    stat(
                        tr("IV a 30 giorni"),
                        format_percent(chain.iv30, 1) if chain.iv30 else "—",
                        sub=tr("indice di volatilità del titolo"),
                        icon="waves",
                    )
                    stat(
                        tr("Dati aggiornati al"),
                        quoted_at(chain.quoted_at),
                        sub=tr("ora USA, ritardo ~15 min"),
                        icon="schedule",
                    )
                    _carry_tiles(view)

        header()

        with ui.row().classes("w-full gap-5 items-start no-wrap max-lg:flex-wrap"):
            with ui.column().classes("gap-5 grow min-w-0 w-full"):

                @ui.refreshable
                def body() -> None:
                    chain, expiry = view.chain, view.expiry
                    if chain is None or expiry is None:
                        with ui.card().classes(CARD):
                            ui.label(
                                tr(
                                    "Scrivi il nome o il simbolo di un titolo e scegli fra i "
                                    "suggerimenti, oppure usa i titoli rapidi. Qualunque "
                                    "simbolo USA con opzioni funziona, anche se non è "
                                    "nell'elenco: scrivilo e premi Invio. Serve internet."
                                )
                            ).classes("text-sm t-muted")
                        return

                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.select(
                            {e: expiry_label(e) for e in chain.expiries},
                            value=expiry,
                            label=tr("Scadenza"),
                            on_change=lambda e: set_expiry(e.value),
                        ).props("dense outlined options-dense").classes("w-[230px]")
                        ui.toggle(
                            {key: tr(key) for key in RANGES},
                            value=view.range_key,
                            on_change=lambda e: set_range(e.value),
                        ).props("dense no-caps unelevated toggle-color=primary").classes(
                            "sim-seg"
                        ).tooltip(tr("Strike mostrati, in percentuale dal prezzo attuale"))

                    with ui.column().classes("w-full gap-0 sim-card sim-tabgroup"):
                        with (
                            ui.tabs()
                            .props("dense no-caps align=left inline-label")
                            .classes("sim-tabs self-start max-w-full") as tabs
                        ):
                            ui.tab("chain", label=tr("Catena"), icon="view_list")
                            ui.tab(
                                "comparison", label=tr("Modello vs mercato"), icon="compare_arrows"
                            )
                            ui.tab("volatility", label=tr("Volatilità"), icon="show_chart")
                        with ui.tab_panels(tabs, value="chain", animated=False).classes(
                            "w-full bg-transparent"
                        ):
                            with ui.tab_panel("chain").classes("p-0 pt-4"):
                                render_chain(view, chain, expiry, ask_side)
                            with ui.tab_panel("comparison").classes("p-0 pt-4"):
                                comparison()
                            with ui.tab_panel("volatility").classes("p-0 pt-4"):
                                volatility_tab()

                @ui.refreshable
                def comparison() -> None:
                    render_comparison(view, comparison.refresh)

                @ui.refreshable
                def volatility_tab() -> None:
                    render_volatility(view)

                body()

            with ui.column().classes("gap-5 w-full lg:w-[340px] shrink-0 lg:sticky lg:top-6"):

                @ui.refreshable
                def basket_card() -> None:
                    render_basket(view, basket_card.refresh)

                basket_card()

    if info.market_ticker and view.chain is None:
        ui.timer(0.05, lambda: load(info.market_ticker), once=True)


# Above this gap, the expiry's own implied yield is shown next to the annual one.
NOISY_YIELD_GAP = 0.005


def _carry_tiles(view: MarketView) -> None:
    """Rate, implied yield, option style and the put-call parity check."""
    carry = view.carry
    if carry is None:
        return
    stat(
        tr("Tasso implicito"),
        format_percent(carry.rate.rate, 2),
        sub=tr(carry.rate.source),
        icon="account_balance",
    )
    q = carry.dividend_yield
    expiry = view.expiry
    this_expiry = carry.dividend(expiry) if expiry is not None else None
    sub = tr("annuo: dividendi + costo di prestito")
    if q is not None and this_expiry is not None and abs(this_expiry - q) > NOISY_YIELD_GAP:
        sub = tr(
            "annuo: dividendi + costo di prestito · questa scadenza: {value}",
            value=format_percent(this_expiry, 2),
        )
    stat(
        tr("Rendimento implicito"),
        format_percent(q, 2) if q is not None else "—",
        sub=sub,
        icon="payments",
    )
    stat(
        tr("Stile delle opzioni"),
        tr("europee") if carry.exercise == "european" else tr("americane"),
        sub=tr("indice: solo a scadenza")
        if carry.exercise == "european"
        else tr("esercitabili sempre"),
        icon="event_available",
    )
    check = view.check
    if check is not None:
        better = check.after < check.before
        stat(
            tr("Verifica call/put"),
            tr("{after} punti", after=format_number(check.after, 2)),
            tone="profit" if better or check.after < 0.6 else "loss",
            sub=tr(
                "differenza di IV fra call e put (con 4% e 0%: {before})",
                before=format_number(check.before, 2),
            ),
            icon="fact_check",
        )
    elif view.checking:
        stat(tr("Verifica call/put"), "…", sub=tr("calcolo in corso"), icon="fact_check")
