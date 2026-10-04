"""La pagina delle opzioni reali: `/mercato`.

--- COSA FA QUESTO FILE ---
Si scrive un titolo USA (AAPL, SPY…), il simulatore scarica da CBOE tutte le
opzioni quotate e le mostra in tre schede, una per file:

  «Catena»              — `chain.py`: la tabella classica dei broker.
  «Modello vs mercato»  — `comparison.py`: una sola volatilità contro i prezzi
                          veri, cioè il sorriso della volatilità.
  «Volatilità»          — `volatility_tab.py`: implicita contro storica.

Il riquadro «Le tue scelte» sta in `basket.py`, lo stato della pagina in
`view.py`. Qui c'è la pagina: ricerca del titolo, caricamento dei dati
(catena, tasso e dividendo, verifica, storico) e disposizione delle parti.
Il lavoro di rete e di calcolo sta in `market_data.py`, `carry.py` e
`volatility.py`.
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
from ...formatting import format_money, format_number, format_percent
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


@ui.page("/mercato")
def market_page() -> None:
    if not auth.require_login():
        return
    info = session.touch(auth.current_username())
    session.STATS.page_views += 1
    view = MarketView(info)

    # Durante il caricamento la pagina si ridisegna e il pulsante premuto
    # sparisce: i messaggi si agganciano quindi alla pagina, che resta.
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
        if chain is None:  # il server si sta spegnendo
            return
        if chain.ticker != info.market_ticker:
            info.market_expiry = None
            info.basket = []
        view.chain = chain
        info.market_ticker = chain.ticker
        view.model_iv = None
        view.reset_carry()
        rate = await run.io_bound(fetch_rate)
        if rate is None:
            return
        view.carry = carry_for(chain, rate)
        view.check = None
        view.loading = False
        view.checking = True
        refresh_all()
        # La verifica ricava centinaia di volatilità implicite: va fatta dopo
        # aver mostrato la catena, non prima.
        view.check = await run.io_bound(parity_check, chain, view.carry)
        view.checking = False
        header.refresh()
        # Per ultimo lo storico dei prezzi, per la scheda «Volatilità».
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
            ui.notify("Selezione svuotata: le gambe devono avere la stessa scadenza.")
        info.market_expiry = value
        view.model_iv = None
        body.refresh()
        basket_card.refresh()

    def set_range(value: str) -> None:
        view.range_key = value
        body.refresh()

    # -- selezione di un'opzione ------------------------------------------

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
            ui.notify("Questa opzione non ha un prezzo utilizzabile.", type="warning")
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
                f"{right.title()} {format_number(strike, 2)}",
                "add_shopping_cart",
                subtitle=f"{display_symbol(view.chain.ticker)} · "
                f"scadenza {view.expiry.strftime('%d/%m/%Y')}",
            )
            ui.label(
                "Chi compra paga il prezzo lettera, chi vende incassa il denaro: la "
                "differenza (lo spread) è il costo nascosto di ogni operazione."
            ).classes(FAINT)
            with ui.row().classes("w-full gap-2 no-wrap"):
                ui.button(
                    f"Compra a {price_text(quote.ask)}",
                    icon="north_east",
                    on_click=lambda: add_leg("long"),
                ).props("unelevated no-caps color=positive").classes("grow").set_enabled(
                    quote.ask > 0
                )
                ui.button(
                    f"Vendi a {price_text(quote.bid)}",
                    icon="south_east",
                    on_click=lambda: add_leg("short"),
                ).props("unelevated no-caps color=negative").classes("grow").set_enabled(
                    quote.bid > 0
                )

        side_dialog_content()

    # -- intestazione: ricerca e dati del titolo --------------------------

    with page_frame(
        "/mercato",
        subtitle="Le opzioni quotate davvero: guardale, scegline alcune e studiale nel "
        "simulatore, o confronta il mercato con il modello.",
    ):

        @ui.refreshable
        def header() -> None:
            with ui.card().classes(CARD):
                card_title(
                    "Carica un titolo",
                    "travel_explore",
                    subtitle=f"Titoli, ETF e indici USA · fonte: {SOURCE_NAME}",
                )
                with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                    ticker_search(
                        label="Cerca un titolo o scrivi un simbolo USA",
                        value=display_symbol(info.market_ticker or ""),
                        on_pick=load,
                        classes="w-[360px] max-w-full",
                    ).props('placeholder="es. Apple, AAPL, Ferrari…"')
                    if view.loading:
                        ui.spinner(size="sm").classes("t-accent")
                    ui.space()
                    for quick in POPULAR:
                        ui.button(display_symbol(quick), on_click=lambda _, t=quick: load(t)).props(
                            "outline dense no-caps color=primary"
                        ).classes("text-xs px-2")

                with (
                    ui.expansion("Sfoglia per categoria", icon="category")
                    .props("dense")
                    .classes("w-full text-sm t-text2")
                ):
                    for category, items in CATALOG.items():
                        with ui.row().classes(
                            "w-full items-start gap-2 no-wrap py-1.5 sim-divider"
                        ):
                            ui.label(category).classes("w-[200px] shrink-0 text-xs t-muted pt-1")
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
                        f"{display_symbol(chain.ticker)} · "
                        f"{company_name(chain.ticker) or 'prezzo'}",
                        format_money(chain.spot),
                        icon="show_chart",
                    )
                    stat(
                        "Variazione del giorno",
                        f"{'+' if chain.change_pct >= 0 else ''}"
                        f"{format_percent(chain.change_pct, 2)}",
                        tone="profit" if chain.change_pct >= 0 else "loss",
                        icon="trending_up" if chain.change_pct >= 0 else "trending_down",
                    )
                    stat(
                        "IV a 30 giorni",
                        format_percent(chain.iv30, 1) if chain.iv30 else "—",
                        sub="indice di volatilità del titolo",
                        icon="waves",
                    )
                    stat(
                        "Dati aggiornati al",
                        quoted_at(chain.quoted_at),
                        sub="ora USA, ritardo ~15 min",
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
                                "Scrivi il nome o il simbolo di un titolo e scegli fra i "
                                "suggerimenti, oppure usa i titoli rapidi. Qualunque "
                                "simbolo USA con opzioni funziona, anche se non è "
                                "nell'elenco: scrivilo e premi Invio. Serve internet."
                            ).classes("text-sm t-muted")
                        return

                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.select(
                            {e: expiry_label(e) for e in chain.expiries},
                            value=expiry,
                            label="Scadenza",
                            on_change=lambda e: set_expiry(e.value),
                        ).props("dense outlined options-dense").classes("w-[230px]")
                        ui.toggle(
                            list(RANGES),
                            value=view.range_key,
                            on_change=lambda e: set_range(e.value),
                        ).props("dense no-caps unelevated toggle-color=primary").classes(
                            "sim-seg"
                        ).tooltip("Strike mostrati, in percentuale dal prezzo attuale")

                    with ui.column().classes("w-full gap-0 sim-card sim-tabgroup"):
                        with (
                            ui.tabs()
                            .props("dense no-caps align=left inline-label")
                            .classes("sim-tabs self-start max-w-full") as tabs
                        ):
                            ui.tab("catena", label="Catena", icon="view_list")
                            ui.tab("confronto", label="Modello vs mercato", icon="compare_arrows")
                            ui.tab("volatilita", label="Volatilità", icon="show_chart")
                        with ui.tab_panels(tabs, value="catena", animated=False).classes(
                            "w-full bg-transparent"
                        ):
                            with ui.tab_panel("catena").classes("p-0 pt-4"):
                                render_chain(view, chain, expiry, ask_side)
                            with ui.tab_panel("confronto").classes("p-0 pt-4"):
                                comparison()
                            with ui.tab_panel("volatilita").classes("p-0 pt-4"):
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


def _carry_tiles(view: MarketView) -> None:
    """Tasso, rendimento implicito, stile e verifica della put-call parity."""
    carry = view.carry
    if carry is None:
        return
    stat(
        "Tasso implicito",
        format_percent(carry.rate.rate, 2),
        sub=carry.rate.source,
        icon="account_balance",
    )
    q = carry.dividend_yield
    stat(
        "Rendimento implicito",
        format_percent(q, 2) if q is not None else "—",
        sub="annuo: dividendi + costo di prestito",
        icon="payments",
    )
    stat(
        "Stile delle opzioni",
        "europee" if carry.exercise == "european" else "americane",
        sub="indice: solo a scadenza" if carry.exercise == "european" else "esercitabili sempre",
        icon="event_available",
    )
    check = view.check
    if check is not None:
        better = check.after < check.before
        stat(
            "Verifica call/put",
            f"{format_number(check.after, 2)} punti",
            tone="profit" if better or check.after < 0.6 else "loss",
            sub=f"differenza di IV fra call e put (con 4% e 0%: {format_number(check.before, 2)})",
            icon="fact_check",
        )
    elif view.checking:
        stat("Verifica call/put", "…", sub="calcolo in corso", icon="fact_check")
