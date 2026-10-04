"""La pagina delle opzioni reali.

--- COSA FA QUESTO FILE ---
Definisce l'indirizzo `/mercato`. Si scrive un titolo USA (AAPL, SPY…), il
simulatore scarica da CBOE tutte le opzioni quotate e le mostra in due schede:

  «Catena»              — la tabella classica dei broker: call a sinistra, put
                          a destra, strike al centro. Cliccando un'opzione la
                          si compra (al prezzo lettera) o vende (al denaro) e
                          finisce fra «Le tue scelte», da aprire nel simulatore.
  «Modello vs mercato»  — ogni strike prezzato dal modello con UNA sola
                          volatilità, accanto al prezzo vero. Lo scarto è il
                          sorriso della volatilità.

Il lavoro di rete e di calcolo sta in `market_data.py`; qui c'è solo
l'interfaccia.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from nicegui import run, ui

from ...pricing import Right
from .. import auth, portfolio, session
from ..carry import (
    DEFAULT_RATE,
    Carry,
    ParityCheck,
    carry_for,
    fetch_rate,
    parity_check,
)
from ..formatting import format_money, format_number, format_percent, format_signed_money
from ..layout import page_frame
from ..market_data import (
    SOURCE_NAME,
    BasketLeg,
    Chain,
    MarketDataError,
    ModelRow,
    Quote,
    fetch_chain,
    model_vs_market,
    position_from_basket,
)
from ..theme import chart_palette
from ..tickers import CATALOG, CATEGORY_TONES, POPULAR, company_name, display_symbol
from ..volatility import VolatilityReport, volatility_report
from ..widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    card_title,
    stat,
    throttled_slider,
    ticker_search,
)

RANGES: dict[str, float | None] = {
    "±5%": 0.05,
    "±10%": 0.10,
    "±20%": 0.20,
    "±35%": 0.35,
    "Tutti": None,
}
DEFAULT_RANGE = "±10%"
CONTRACT_MULTIPLIER = 100

SIDE_CELLS = ["Denaro", "Lettera", "IV", "Δ", "OI"]


class MarketView:
    """Stato della pagina: catena caricata e impostazioni dei controlli."""

    def __init__(self, info: session.SessionInfo) -> None:
        self.info = info
        self.chain: Chain | None = None
        self.loading = False
        self.range_key = DEFAULT_RANGE
        self.model_iv: float | None = None  # None = IV ATM della scadenza
        # Tasso, dividendo e stile ricavati dal mercato; le versioni «manual_»
        # sono quelle scritte a mano nel confronto (None = usa i ricavati).
        self.carry: Carry | None = None
        self.check: ParityCheck | None = None
        self.checking = False
        # Scheda «Volatilità»: storico e confronto con la IV.
        self.vol: VolatilityReport | None = None
        self.vol_error: str | None = None
        self.vol_loading = False
        self.manual_rate: float | None = None
        self.manual_dividend: float | None = None
        self.manual_exercise: str | None = None
        self.pending: tuple[Right, float] | None = None

    @property
    def rate(self) -> float:
        if self.manual_rate is not None:
            return self.manual_rate
        return self.carry.rate.rate if self.carry else DEFAULT_RATE

    def dividend(self, expiry: date) -> float:
        if self.manual_dividend is not None:
            return self.manual_dividend
        return self.carry.dividend(expiry) if self.carry else 0.0

    @property
    def exercise(self) -> str:
        if self.manual_exercise is not None:
            return self.manual_exercise
        return self.carry.exercise if self.carry else "american"

    def reset_carry(self) -> None:
        self.manual_rate = self.manual_dividend = self.manual_exercise = None

    @property
    def expiry(self) -> date | None:
        if self.chain is None:
            return None
        chosen = self.info.market_expiry
        if chosen in self.chain.quotes:
            return chosen
        # Prima scadenza ad almeno una settimana: le giornaliere sono rumorose.
        later = [e for e in self.chain.expiries if (e - date.today()).days >= 7]
        return later[0] if later else self.chain.expiries[0]

    def visible_strikes(self) -> list[float]:
        if self.chain is None or self.expiry is None:
            return []
        strikes = self.chain.strikes(self.expiry)
        width = RANGES[self.range_key]
        if width is None:
            return strikes
        spot = self.chain.spot
        return [k for k in strikes if abs(k - spot) <= spot * width]


def _expiry_label(expiry: date) -> str:
    days = (expiry - date.today()).days
    return f"{expiry.strftime('%d/%m/%Y')} · {days} gg"


def _quoted_at(raw: str) -> str:
    """``2026-10-03 03:44:04`` di CBOE diventa ``03/10 03:44``."""
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
    except ValueError:
        return raw or "—"


def _price(value: float | None) -> str:
    return "—" if value is None or value <= 0 else format_number(value, 2)


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
                    f"Compra a {_price(quote.ask)}",
                    icon="north_east",
                    on_click=lambda: add_leg("long"),
                ).props("unelevated no-caps color=positive").classes("grow").set_enabled(
                    quote.ask > 0
                )
                ui.button(
                    f"Vendi a {_price(quote.bid)}",
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
                        _quoted_at(chain.quoted_at),
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
                            {e: _expiry_label(e) for e in chain.expiries},
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
                                _chain_table(view, chain, expiry, ask_side)
                            with ui.tab_panel("confronto").classes("p-0 pt-4"):
                                comparison()
                            with ui.tab_panel("volatilita").classes("p-0 pt-4"):
                                volatility_tab()

                @ui.refreshable
                def comparison() -> None:
                    _comparison(view, comparison.refresh)

                @ui.refreshable
                def volatility_tab() -> None:
                    _volatility(view)

                body()

            with ui.column().classes("gap-5 w-full lg:w-[340px] shrink-0 lg:sticky lg:top-6"):

                @ui.refreshable
                def basket_card() -> None:
                    _basket(view, basket_card.refresh)

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


# ---------------------------------------------------------------------------
# Scheda «Catena»
# ---------------------------------------------------------------------------


def _side_cells(quote: Quote | None, *, mirrored: bool) -> None:
    values = (
        ["—"] * 5
        if quote is None
        else [
            _price(quote.bid),
            _price(quote.ask),
            format_percent(quote.iv, 1) if quote.iv else "—",
            format_number(quote.delta, 2) if quote.delta is not None else "—",
            format_number(quote.open_interest, 0),
        ]
    )
    if mirrored:
        values = values[::-1]
    for value in values:
        ui.label(value).classes("w-[62px] text-right")


def _chain_table(view: MarketView, chain: Chain, expiry: date, on_pick: Any) -> None:
    strikes = view.visible_strikes()
    spot = chain.spot
    with ui.column().classes("w-full gap-0 overflow-x-auto"):
        with ui.row().classes("min-w-[760px] w-full no-wrap gap-0 pb-1"):
            ui.label("CALL").classes("grow basis-0 text-center sim-eyebrow")
            ui.label("").classes("w-[90px]")
            ui.label("PUT").classes("grow basis-0 text-center sim-eyebrow")
        with ui.row().classes("min-w-[760px] w-full no-wrap gap-0 sim-thead pb-2"):
            with ui.row().classes("grow basis-0 no-wrap gap-1 justify-end pr-2"):
                for name in SIDE_CELLS[::-1]:
                    ui.label(name).classes("w-[62px] text-right")
            ui.label("Strike").classes("w-[90px] text-center")
            with ui.row().classes("grow basis-0 no-wrap gap-1 pl-2"):
                for name in SIDE_CELLS:
                    ui.label(name).classes("w-[62px] text-right")

        spot_drawn = False
        for strike in strikes:
            if not spot_drawn and strike >= spot:
                spot_drawn = True
                with ui.row().classes("min-w-[760px] w-full items-center gap-2 no-wrap py-0.5"):
                    ui.element("div").classes("grow h-px").style("background: var(--info)")
                    ui.label(f"prezzo {format_number(spot, 2)}").classes(
                        "text-[11px] font-semibold"
                    ).style("color: var(--info)")
                    ui.element("div").classes("grow h-px").style("background: var(--info)")
            call = chain.quote(expiry, "call", strike)
            put = chain.quote(expiry, "put", strike)
            with ui.row().classes(
                "min-w-[760px] w-full no-wrap gap-0 text-[13px] t-text2 t-num sim-divider"
            ):
                with (
                    ui.row()
                    .classes(
                        "grow basis-0 no-wrap gap-1 justify-end pr-2 py-1.5 cursor-pointer "
                        "sim-chain-cell" + (" sim-itm" if strike < spot else "")
                    )
                    .on("click", lambda _, k=strike: on_pick("call", k))
                ):
                    _side_cells(call, mirrored=True)
                ui.label(format_number(strike, 2)).classes(
                    "w-[90px] text-center font-semibold t-text py-1.5"
                )
                with (
                    ui.row()
                    .classes(
                        "grow basis-0 no-wrap gap-1 pl-2 py-1.5 cursor-pointer sim-chain-cell"
                        + (" sim-itm" if strike > spot else "")
                    )
                    .on("click", lambda _, k=strike: on_pick("put", k))
                ):
                    _side_cells(put, mirrored=False)
    ui.label(
        "Le righe colorate sono in the money. Clicca il lato call o put di una riga "
        "per comprare o vendere quell'opzione."
    ).classes(FAINT + " mt-2")


# ---------------------------------------------------------------------------
# Scheda «Modello vs mercato»
# ---------------------------------------------------------------------------


def _comparison(view: MarketView, refresh: Any) -> None:
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
        "Il modello con una sola volatilità, contro il mercato",
        "compare_arrows",
        subtitle="Il modello prezza ogni strike con la stessa IV; il mercato no. "
        "Lo scarto, strike per strike, è il sorriso della volatilità.",
    )
    with ui.row().classes("w-full items-end gap-x-6 gap-y-2 flex-wrap"):
        with ui.column().classes("gap-0 grow min-w-[240px]"):
            ui.label(
                f"IV del modello: {format_percent(iv, 1)} "
                f"(ATM di mercato: {format_percent(atm, 1)})"
            ).classes("text-xs t-muted")
            throttled_slider(
                minimum=5, maximum=150, step=0.5, value=round(iv * 100, 1), on_value=set_iv
            ).classes("w-full")
        ui.button("IV ATM", icon="restart_alt", on_click=reset_iv).props(
            "flat dense no-caps color=primary"
        ).classes("text-xs")
        ui.number(
            "Tasso",
            value=round(view.rate * 100, 2),
            step=0.25,
            format="%.2f",
            on_change=lambda e: set_rate(e.value),
        ).props("dense outlined suffix=%").classes("w-[110px]")
        ui.number(
            "Dividendo",
            value=round(view.dividend(expiry) * 100, 2),
            step=0.25,
            format="%.2f",
            on_change=lambda e: set_dividend(e.value),
        ).props("dense outlined suffix=%").classes("w-[110px]").tooltip(
            "Rendimento implicito per questa scadenza, ricavato dalla catena"
        )
        ui.toggle(
            {"american": "Americana", "european": "Europea"},
            value=view.exercise,
            on_change=lambda e: set_exercise(e.value),
        ).props("dense no-caps unelevated toggle-color=primary").classes("sim-seg")
        manual = (view.manual_rate, view.manual_dividend, view.manual_exercise)
        if any(v is not None for v in manual):
            ui.button("Valori del mercato", icon="restart_alt", on_click=use_market_values).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

    c = chart_palette()
    with ui.row().classes("w-full gap-4 no-wrap max-xl:flex-wrap mt-2"):
        with ui.column().classes("grow basis-0 min-w-[300px] gap-1"):
            ui.label("Volatilità implicita per strike").classes("text-sm font-semibold t-text")
            ui.echart(_smile_option(rows, chain.spot, iv, c)).classes("w-full h-[300px]")
        with ui.column().classes("grow basis-0 min-w-[300px] gap-1"):
            ui.label("Mercato meno modello ($ per azione)").classes("text-sm font-semibold t-text")
            ui.echart(_gap_option(rows, chain.spot, c)).classes("w-full h-[300px]")

    _comparison_table(rows, chain.spot)
    ui.label(
        "* Scarto = prezzo di mercato meno prezzo del modello. Rosso: il mercato "
        "chiede di più; verde: di meno. OI = interesse aperto, cioè quanti "
        "contratti esistono su quell'opzione."
    ).classes(FAINT + " mt-1")

    ui.label(
        "Tasso e dividendo non sono inventati: vengono dalla put-call parity. Una call "
        "comprata e una put venduta allo stesso strike equivalgono a possedere il "
        "titolo a termine, quindi C − P rivela il forward. Dall'S&P 500, che ha "
        "opzioni europee, si ricava il tasso; dal forward di ogni titolo il suo "
        "rendimento implicito. Con valori giusti, call e put allo stesso strike "
        "hanno la stessa IV: la casella «Verifica call/put» misura quanto ci si "
        "avvicina."
    ).classes(FAINT + " mt-2")
    ui.label(
        "Come leggerlo. Se il modello avesse ragione, la IV di mercato sarebbe una "
        "linea piatta e le barre sarebbero tutte a zero. Sulle azioni di solito le "
        "put molto fuori dal denaro (strike bassi) costano più del modello: il "
        "mercato paga una protezione contro i crolli che la lognormale considera "
        "quasi impossibili. Barre positive = il mercato chiede più del modello."
    ).classes(FAINT + " mt-2")


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
                ui.label(text).classes("w-[72px] text-right")
            ui.label("Strike").classes("grow text-center")
            for text in ["Put merc.", "Put mod.", "Scarto*"]:
                ui.label(text).classes("w-[72px] text-right")
        for row in rows:
            near = abs(row.strike - spot) <= spot * 0.01
            with ui.row().classes(
                "min-w-[640px] w-full no-wrap gap-1 text-[13px] t-text2 t-num py-1 px-1 "
                "sim-divider" + (" sim-itm" if near else "")
            ):
                ui.label(_price(row.call_market)).classes("w-[72px] text-right")
                ui.label(format_number(row.call_model, 2)).classes("w-[72px] text-right")
                gap_cell(row.call_market, row.call_model)
                ui.label(format_number(row.strike, 2)).classes(
                    "grow text-center font-semibold t-text"
                )
                ui.label(_price(row.put_market)).classes("w-[72px] text-right")
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
        "label": {"formatter": "prezzo", "color": c["spot"], "fontSize": 10},
    }


def _smile_option(
    rows: list[ModelRow], spot: float, iv: float, c: dict[str, str]
) -> dict[str, Any]:
    def points(attr: str) -> list[list[float]]:
        return [
            [r.strike, round(getattr(r, attr) * 100, 2)]
            for r in rows
            if getattr(r, attr) is not None
        ]

    strikes = [r.strike for r in rows] or [spot]
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
                "name": "IV call",
                "type": "line",
                "data": points("call_iv"),
                "symbolSize": 5,
                "lineStyle": {"color": c["profit"], "width": 2},
                "itemStyle": {"color": c["profit"]},
                "markLine": _spot_line(spot, c),
            },
            {
                "name": "IV put",
                "type": "line",
                "data": points("put_iv"),
                "symbolSize": 5,
                "lineStyle": {"color": c["loss"], "width": 2},
                "itemStyle": {"color": c["loss"]},
            },
            {
                "name": "Modello",
                "type": "line",
                "data": [[min(strikes), iv * 100], [max(strikes), iv * 100]],
                "showSymbol": False,
                "lineStyle": {"color": c["forward"], "width": 2, "type": "dashed"},
                "itemStyle": {"color": c["forward"]},
            },
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
                "name": "Call",
                "type": "bar",
                "data": gaps("call_market", "call_model"),
                "barWidth": width,
                "itemStyle": {"color": c["profit"], "borderRadius": 2},
                "markLine": _spot_line(spot, c),
            },
            {
                "name": "Put",
                "type": "bar",
                "data": gaps("put_market", "put_model"),
                "barWidth": width,
                "itemStyle": {"color": c["loss"], "borderRadius": 2},
            },
        ],
    }


# ---------------------------------------------------------------------------
# Scheda «Volatilità»: care o economiche?
# ---------------------------------------------------------------------------

VERDICTS: dict[str, tuple[str, str, str]] = {
    # verdetto -> (titolo, colore, spiegazione)
    "care": (
        "Opzioni care",
        "var(--loss)",
        "Il mercato si aspetta più movimento di quello che il titolo ha fatto "
        "nell'ultimo mese, oppure c'è un evento in arrivo (per esempio gli utili "
        "trimestrali). Chi vende opzioni incassa premi alti; chi le compra paga caro "
        "e rischia il vol crush quando l'evento passa.",
    ),
    "nella media": (
        "Opzioni nella media",
        "var(--info)",
        "La volatilità implicita è in linea con quella realizzata, con il piccolo "
        "sovrapprezzo che il mercato chiede di solito. Nessun vantaggio evidente né "
        "per chi compra né per chi vende.",
    ),
    "economiche": (
        "Opzioni economiche",
        "var(--profit)",
        "Il mercato prezza meno movimento di quello che il titolo sta facendo davvero. "
        "Comprare opzioni costa poco rispetto all'agitazione recente; vendere "
        "opzioni incassa poco per il rischio che si prende.",
    ),
}


def _volatility(view: MarketView) -> None:
    card_title(
        "Volatilità implicita contro storica",
        "show_chart",
        tone="violet",
        subtitle="La IV è quanto il mercato si aspetta che il titolo si muova; la "
        "storica è quanto si è mosso davvero. Confrontarle dice se le opzioni sono "
        "care o economiche.",
    )
    if view.vol_loading:
        with ui.row().classes("items-center gap-2"):
            ui.spinner(size="sm").classes("t-accent")
            ui.label("Scarico lo storico dei prezzi…").classes("text-sm t-muted")
        return
    if view.vol_error:
        ui.label(view.vol_error).classes("text-sm t-muted")
        return
    report = view.vol
    if report is None:
        ui.label("Carica un titolo per vedere la sua volatilità.").classes("text-sm t-muted")
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
            ui.label(title).classes("t-serif text-[24px] leading-tight").style(f"color: {color}")
            ui.label(
                f"La IV a 30 giorni ({format_percent(report.iv, 1)}) è "
                f"{format_number(report.ratio, 2)} volte la volatilità realizzata "
                f"nell'ultimo mese ({format_percent(report.hv20, 1)}). {text}"
            ).classes("text-sm t-text2 leading-relaxed")

    with ui.element("div").classes("w-full grid gap-2 grid-cols-2 md:grid-cols-3"):
        stat(
            "Implicita a 30 giorni",
            format_percent(report.iv, 1) if report.iv is not None else "—",
            sub="quanto il mercato si aspetta",
            icon="visibility",
        )
        stat(
            "Storica 1 mese",
            format_percent(report.hv20, 1),
            sub="20 giorni di borsa",
            icon="history",
        )
        stat(
            "Storica 3 mesi",
            format_percent(report.hv60, 1),
            sub="60 giorni di borsa",
            icon="history",
        )
        stat(
            "Storica 1 anno",
            format_percent(report.hv252, 1),
            sub="252 giorni di borsa",
            icon="history",
        )
        stat(
            "Implicita / storica",
            f"{format_number(report.ratio, 2)}×" if report.ratio is not None else "—",
            sub="sopra 1 = il mercato prevede più movimento",
            icon="balance",
        )
        stat(
            "Posizione nell'anno",
            format_percent(report.percentile, 0) if report.percentile is not None else "—",
            sub="giorni dell'ultimo anno con storica più bassa della IV di oggi",
            icon="leaderboard",
        )

    c = chart_palette()
    days = [d.strftime("%d/%m/%y") for d, _ in report.rolling]
    price_by_day = {p.day: p.close for p in report.prices}
    series: list[dict[str, Any]] = [
        {
            "name": "Storica a 30 giorni",
            "type": "line",
            "data": [round(v * 100, 2) for _, v in report.rolling],
            "showSymbol": False,
            "lineStyle": {"color": c["forward"], "width": 2},
            "itemStyle": {"color": c["forward"]},
            "areaStyle": {"color": c["forward"], "opacity": 0.08},
        },
        {
            "name": f"Prezzo {display_symbol(report.source)}",
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
                "name": "Implicita di oggi",
                "type": "line",
                "data": [round(report.iv * 100, 2)] * len(days),
                "showSymbol": False,
                "lineStyle": {"color": c["today"], "width": 2, "type": "dashed"},
                "itemStyle": {"color": c["today"]},
            }
        )
    ui.label("Volatilità storica nell'ultimo anno, contro la implicita di oggi").classes(
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
        "Storica = deviazione standard dei rendimenti giornalieri, annualizzata (×√252). "
        "La IV sta di solito un po' sopra la storica anche in tempi normali: chi vende "
        "opzioni chiede un premio per il rischio di movimenti improvvisi. Per questo "
        "«care» scatta solo quando la IV supera la storica di oltre il 25%."
        + (
            f" Per gli indici CBOE non fornisce lo storico: si usa {display_symbol(report.source)}, "  # noqa: E501
            "l'ETF che li replica."
            if proxy
            else ""
        )
    ).classes(FAINT + " mt-2")


# ---------------------------------------------------------------------------
# Le tue scelte
# ---------------------------------------------------------------------------


def _basket(view: MarketView, refresh: Any) -> None:
    info = view.info
    basket = info.basket

    def remove(index: int) -> None:
        del basket[index]
        refresh()

    def set_qty(index: int, value: Any) -> None:
        if value:
            leg = basket[index]
            basket[index] = BasketLeg(
                right=leg.right,
                side=leg.side,
                strike=leg.strike,
                qty=max(1, round(float(value))),
                premium=leg.premium,
                iv=leg.iv,
            )
            refresh()

    def clear() -> None:
        basket.clear()
        refresh()

    def open_in_simulator() -> None:
        chain, expiry = view.chain, info.market_expiry
        if chain is None or expiry is None or not basket:
            return
        state = position_from_basket(
            chain,
            expiry,
            list(basket),
            risk_free_rate=view.rate,
            dividend_yield=view.dividend(expiry),
            exercise=view.exercise,  # type: ignore[arg-type]
        )
        session.replace_position(state)
        ui.navigate.to("/")

    def open_in_portfolio() -> None:
        chain, expiry = view.chain, info.market_expiry
        username = auth.current_username()
        if chain is None or expiry is None or not basket or username is None:
            return
        cost = (
            sum((1 if leg.side == "long" else -1) * leg.premium * leg.qty for leg in basket)
            * CONTRACT_MULTIPLIER
        )

        with ui.dialog() as dialog, ui.card().classes("sim-card w-[460px] max-w-full gap-3"):
            card_title(
                "Apri nel portafoglio virtuale",
                "account_balance_wallet",
                subtitle=f"{display_symbol(chain.ticker)} · scadenza {expiry.strftime('%d/%m/%Y')}",
            )
            ui.label(
                f"{'Pagheresti' if cost >= 0 else 'Incasseresti'} "
                f"{format_money(abs(cost))} (prezzi reali, {CONTRACT_MULTIPLIER} azioni per "
                "contratto). Nessun soldo vero: il simulatore ricorda solo i prezzi e la "
                "previsione del modello, per confrontarli poi con quello che succede."
            ).classes("text-sm t-muted")
            note = (
                ui.textarea(
                    "La tua previsione (facoltativa)",
                    placeholder="es. credo che salga sopra 340 prima della scadenza",
                )
                .props("dense outlined autogrow maxlength=300")
                .classes("w-full")
            )

            def confirm() -> None:
                try:
                    portfolio.open_position(
                        username,
                        chain,
                        expiry,
                        list(basket),
                        rate=view.rate,
                        dividend=view.dividend(expiry),
                        exercise=view.exercise,
                        note=note.value or "",
                    )
                except ValueError as error:
                    ui.notify(str(error), type="negative")
                    return
                dialog.close()
                basket.clear()
                refresh()
                ui.notify("Posizione aperta nel portafoglio virtuale", type="positive")
                ui.navigate.to("/portafoglio")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Annulla", on_click=dialog.close).props("flat no-caps").classes("t-muted")
                ui.button("Apri la posizione", icon="check", on_click=confirm).props(
                    "unelevated no-caps"
                )
        dialog.open()

    with ui.card().classes(CARD):
        expiry = info.market_expiry
        card_title(
            "Le tue scelte",
            "shopping_cart",
            subtitle=(
                f"{display_symbol(info.market_ticker)} · scadenza {expiry.strftime('%d/%m/%Y')}"
                if basket and expiry
                else "Clicca un'opzione nella catena"
            ),
        )
        if not basket:
            ui.label(
                "Qui si raccolgono le opzioni che compri o vendi dalla catena. Tutte "
                "devono avere la stessa scadenza: cambiando scadenza la selezione "
                "riparte da capo."
            ).classes(FAINT)
            return

        net = 0.0
        for index, leg in enumerate(basket):
            sign = 1 if leg.side == "long" else -1
            net += sign * leg.premium * leg.qty
            with ui.row().classes("w-full items-center gap-2 no-wrap py-2 sim-divider"):
                ui.label("L" if leg.side == "long" else "S").classes("sim-chip").style(
                    f"color: {COLOR_PROFIT if leg.side == 'long' else COLOR_LOSS}"
                )
                with ui.column().classes("gap-0 grow min-w-0"):
                    ui.label(
                        f"{'Long' if leg.side == 'long' else 'Short'} {leg.right} "
                        f"{format_number(leg.strike, 2)}"
                    ).classes("text-sm t-text")
                    ui.label(
                        f"a {format_number(leg.premium, 2)}"
                        + (f" · IV {format_percent(leg.iv, 1)}" if leg.iv else "")
                    ).classes("text-[11px] t-faint")
                ui.number(
                    value=leg.qty,
                    min=1,
                    step=1,
                    format="%.0f",
                    on_change=lambda e, i=index: set_qty(i, e.value),
                ).props("dense outlined").classes("w-[64px]")
                ui.button(icon="close", on_click=lambda _, i=index: remove(i)).props(
                    "flat dense round size=sm"
                ).classes("t-faint")

        debit = net >= 0
        with ui.row().classes("w-full justify-between items-baseline mt-2"):
            ui.label("Costo netto (debito)" if debit else "Credito netto").classes(
                "text-xs t-muted"
            )
            ui.label(format_signed_money(-net)).classes("text-base font-semibold t-num").style(
                f"color: {COLOR_LOSS if debit else COLOR_PROFIT}"
            )
        ui.label(
            f"Per azione. Un contratto vale {CONTRACT_MULTIPLIER} azioni: "
            f"{format_signed_money(-net * CONTRACT_MULTIPLIER)} per contratto."
        ).classes(FAINT)

        ui.button(
            "Apri nel portafoglio", icon="account_balance_wallet", on_click=open_in_portfolio
        ).props("unelevated no-caps").classes("w-full py-2 mt-2").tooltip(
            "Registra la posizione ai prezzi veri e seguila nei prossimi giorni"
        )
        ui.button(
            "Studia nel simulatore", icon="candlestick_chart", on_click=open_in_simulator
        ).props("outline no-caps color=primary").classes("w-full py-2")
        ui.button("Svuota", icon="delete_outline", on_click=clear).props(
            "flat dense no-caps"
        ).classes("w-full t-muted text-xs")
        ui.label(
            "Nel simulatore spot, giorni, IV, tasso e dividendo vengono dal mercato "
            "e i premi pagati sono quelli reali. Sostituisce la posizione aperta: "
            "salvala prima, se ti serve."
        ).classes(FAINT)
