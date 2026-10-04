"""Pannelli dell'interfaccia.

--- COSA FA QUESTO FILE ---
Contiene i blocchi visivi dell'applicazione: mercato, strategie, gambe,
riepilogo, greche, simulatore di scenari, costi. Ogni pannello è una funzione che
riceve il contesto di pagina e disegna se stessa.

Nessun pannello calcola niente di finanziario: i numeri arrivano già pronti da
`ctx.analytics`. Così le pagine si compongono scegliendo quali pannelli
mostrare, senza duplicare logica.
"""

from __future__ import annotations

import base64
from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from nicegui import events, ui

from ..pricing import StockLeg, moneyness
from . import auth, saved, session
from .context import PageContext
from .formatting import (
    format_expiry,
    format_money,
    format_number,
    format_percent,
    format_signed_money,
)
from .state import MATRIX_IV_MOVES, MATRIX_PRICE_MOVES, PositionState, Scenario
from .strategies import (
    CUSTOM_STRATEGY,
    CUSTOM_STRATEGY_DESCRIPTION,
    CUSTOM_STRATEGY_NAME,
    STRATEGIES,
)
from .theme import chart_palette
from .tickers import company_name, display_symbol
from .widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    DANGER_STRIP,
    FAINT,
    MONEYNESS_COLOR,
    MUTED,
    card_title,
    commit_on_leave,
    stat,
    throttled_slider,
    ticker_search,
)

GREEK_ROWS: list[tuple[str, str, str, str, str]] = [
    (
        "Δ",
        "Delta",
        "delta",
        "",
        "Variazione del valore della posizione per +1 $ del sottostante. "
        "È l'esposizione direzionale netta.",
    ),
    (
        "Γ",
        "Gamma",
        "gamma",
        "",
        "Variazione del delta per +1 $ del sottostante. Misura quanto "
        "rapidamente cambia l'esposizione direzionale.",
    ),
    (
        "Θ",
        "Theta",
        "theta_per_day",
        "$/gg",
        "Variazione del valore per ogni giorno che passa. Negativo per chi è "
        "net long di opzioni: il tempo erode il premio.",
    ),
    (
        "ν",
        "Vega",
        "vega_per_point",
        "$/1% IV",
        "Variazione del valore per +1 punto di volatilità implicita. Net short "
        "vega guadagna da un vol crush.",
    ),
    (
        "ρ",
        "Rho",
        "rho_per_point",
        "$/1% tasso",
        "Variazione del valore per +1 punto di tasso risk-free. La greca meno "
        "rilevante per scadenze brevi.",
    ),
]


# ---------------------------------------------------------------------------
# Mercato
# ---------------------------------------------------------------------------


def market_panel(ctx: PageContext) -> None:
    state = ctx.state
    m = state.market

    def set_field(name: str, value: Any) -> None:
        if value is None:
            return
        state.set_market(**{name: float(value)})
        ctx.rerender()

    references = [
        leg.entry_price if isinstance(leg, StockLeg) else leg.strike for leg in state.legs
    ]

    with ui.card().classes(CARD):
        card_title("Sottostante e mercato", "tune")
        with ui.row().classes("w-full gap-2 no-wrap"):
            # Ticker e nome sono collegati: scegliendo un titolo in uno dei due
            # campi si compilano entrambi, con le stesse scritture del catalogo.
            ticker_search(
                label="Ticker",
                value=display_symbol(state.ticker),
                on_pick=lambda s: _set_symbol(ctx, s),
                classes="w-[38%] shrink-0",
                commit_on_blur=True,
            )
            ticker_search(
                label="Nome",
                value=state.name,
                on_pick=lambda s: _set_symbol(ctx, s),
                on_text=lambda t: _set_text(ctx, "name", t),
                classes="grow",
                commit_on_blur=True,
                mode="name",
                align_right=True,
            )

        commit_on_leave(
            ui.number("Prezzo spot", value=m.spot, step=0.5, format="%.2f")
            .classes("w-full")
            .props("dense outlined suffix=$"),
            lambda v: set_field("spot", v),
        )
        throttled_slider(
            minimum=max(min(references) * 0.5, 1.0),
            maximum=max(references) * 1.5,
            step=0.5,
            value=m.spot,
            on_value=lambda v: set_field("spot", v),
        ).classes("w-full")

        commit_on_leave(
            ui.number("Giorni alla scadenza", value=m.days_to_expiry, step=1, format="%.0f")
            .classes("w-full")
            .props(f'dense outlined suffix="gg · scade {format_expiry(m.days_to_expiry)}"'),
            lambda v: set_field("days_to_expiry", v),
        )
        throttled_slider(
            minimum=0,
            maximum=365,
            step=1,
            value=m.days_to_expiry,
            on_value=lambda v: set_field("days_to_expiry", v),
        ).classes("w-full")

        commit_on_leave(
            ui.number("Volatilità implicita (IV)", value=m.iv * 100, step=1, format="%.1f")
            .classes("w-full")
            .props("dense outlined suffix=%"),
            lambda v: set_field("iv", (v or 0) / 100),
        )
        throttled_slider(
            minimum=1,
            maximum=150,
            step=1,
            value=m.iv * 100,
            on_value=lambda v: set_field("iv", v / 100),
        ).classes("w-full")

        with ui.row().classes("w-full gap-2 no-wrap"):
            commit_on_leave(
                ui.number("Tasso risk-free", value=m.risk_free_rate * 100, step=0.25, format="%.2f")
                .classes("grow")
                .props("dense outlined suffix=%"),
                lambda v: set_field("risk_free_rate", (v or 0) / 100),
            )
            commit_on_leave(
                ui.number("Dividend yield", value=m.dividend_yield * 100, step=0.25, format="%.2f")
                .classes("grow")
                .props("dense outlined suffix=%"),
                lambda v: set_field("dividend_yield", (v or 0) / 100),
            )

        ui.separator().classes("my-3")
        ui.label("Stile di esercizio").classes(MUTED + " font-medium")
        ui.toggle(
            {"european": "Europea", "american": "Americana"},
            value=state.exercise,
            on_change=lambda e: _set_exercise(ctx, e.value),
        ).props("dense no-caps unelevated spread toggle-color=primary").classes("w-full sim-seg")
        ui.label(
            "Esercitabile solo a scadenza. Prezzata con Black-Scholes-Merton (formula chiusa)."
            if state.exercise == "european"
            else "Esercitabile in qualsiasi momento. Prezzata con albero binomiale "
            "CRR: include il valore dell'esercizio anticipato, visibile "
            "soprattutto sulle put ITM."
        ).classes(FAINT)
        other = "americane" if state.exercise == "european" else "europee"
        ui.switch(
            f"Confronta sul grafico: se fossero {other}",
            value=state.compare_exercise,
            on_change=lambda e: _set_compare(ctx, e.value),
        ).props("dense").classes("mt-1 text-xs")
        if state.compare_exercise:
            ui.label(
                "La curva verde acqua usa gli stessi premi pagati: la distanza dalla "
                "viola è solo il valore dell'esercizio anticipato. Per una call senza "
                "dividendi le due curve coincidono."
            ).classes(FAINT)


def _set_symbol(ctx: PageContext, symbol: str) -> None:
    """Imposta insieme ticker e nome, dal catalogo.

    Il ticker si salva nella forma da mostrare (``SPX``, mai ``_SPX`` o
    ``^SPX``). Se il simbolo non è nel catalogo il nome diventa il simbolo
    stesso, così non resta mai il nome di un'azienda diversa.
    """
    shown = display_symbol(symbol)
    if not shown:
        return
    ctx.state.ticker = shown
    ctx.state.name = company_name(symbol) or shown
    ctx.rerender()


def _set_text(ctx: PageContext, attribute: str, value: str) -> None:
    """Testo libero (il nome scritto a mano): non entra in nessun calcolo."""
    setattr(ctx.state, attribute, value)
    ctx.rerender()


def _set_exercise(ctx: PageContext, value: str) -> None:
    ctx.state.exercise = value  # type: ignore[assignment]
    ctx.rerender()


def _set_compare(ctx: PageContext, value: bool) -> None:
    ctx.state.compare_exercise = value
    ctx.rerender()


# ---------------------------------------------------------------------------
# Strategie e premi d'ingresso
# ---------------------------------------------------------------------------


def strategy_panel(ctx: PageContext) -> None:
    state = ctx.state

    def apply(key: str) -> None:
        state.apply_strategy(key)
        ctx.rerender()

    def set_pin(value: bool) -> None:
        state.set_pin_premiums(value)
        ctx.rerender()

    def reprice() -> None:
        state.reprice_entry()
        ui.notify("Premi rifissati ai prezzi correnti", type="positive")
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title("Strategie precostruite", "auto_awesome")
        options = {key: s.name for key, s in STRATEGIES.items()}
        if state.strategy_key not in options:
            options = {CUSTOM_STRATEGY: CUSTOM_STRATEGY_NAME, **options}
        ui.select(
            options,
            value=state.strategy_key if state.strategy_key in options else CUSTOM_STRATEGY,
            on_change=lambda e: apply(e.value),
        ).classes("w-full").props("dense outlined")
        strategy = STRATEGIES.get(state.strategy_key)
        ui.label(
            strategy.description if strategy is not None else CUSTOM_STRATEGY_DESCRIPTION
        ).classes(FAINT)

        ui.separator().classes("my-3")
        ui.label("Premi d'ingresso").classes(MUTED + " font-medium")
        ui.switch(
            "Congelati all'apertura della posizione",
            value=state.pin_premiums,
            on_change=lambda e: set_pin(e.value),
        ).props("dense")
        ui.label(
            "Il costo già pagato non cambia quando muovi lo spot: è il "
            "comportamento corretto. Disattivandolo, i premi vengono riprezzati "
            "ai parametri correnti e la curva «valore oggi» passerà sempre per "
            "lo zero al prezzo spot."
            if state.pin_premiums
            else "I premi seguono i parametri correnti: muovendo lo spot cambia "
            "anche il costo «già pagato», e i break-even scivolano con lo slider."
        ).classes(FAINT)

        if state.pin_premiums:
            entry = state.entry_market
            moved = (
                abs(entry.spot - state.market.spot) > 1e-9
                or abs(entry.iv - state.market.iv) > 1e-12
                or abs(entry.days_to_expiry - state.market.days_to_expiry) > 1e-9
            )
            if moved:
                ui.label(
                    f"Premi fissati a: spot {format_number(entry.spot, 2)} $ · "
                    f"IV {format_percent(entry.iv, 1)} · "
                    f"{format_number(entry.days_to_expiry, 0)} gg. "
                    "Anche le gambe aggiunte ora usano questi valori."
                ).classes("text-[11px] leading-relaxed mt-1 px-2.5 py-1.5 sim-warn")
            ui.button(
                "Rifissa i premi ai prezzi correnti", icon="push_pin", on_click=reprice
            ).props("outline dense no-caps color=primary").classes("text-xs px-3 mt-1")


# ---------------------------------------------------------------------------
# Comandi sopra il grafico
# ---------------------------------------------------------------------------

NO_COMPARISON = ""


def chart_controls_panel(ctx: PageContext) -> None:
    """Tempo che scorre, confronto con una posizione salvata, esportazione."""
    state = ctx.state
    dte = state.market.days_to_expiry
    forward = min(state.days_forward, dte)
    playing = ctx.animation is not None and ctx.animation.active

    def set_forward(value: float) -> None:
        state.days_forward = value
        ctx.rerender()

    def toggle_play() -> None:
        if ctx.animation is None:
            return
        if ctx.animation.active:
            ctx.animation.deactivate()
        else:
            if state.days_forward >= dte:
                state.days_forward = 0.0
            ctx.animation.activate()
        ctx.rerender()

    def set_comparison(position_id: str) -> None:
        username = auth.current_username()
        item = saved.get(username, position_id) if username and position_id else None
        if item is None:
            state.comparison, state.comparison_name = None, ""
        else:
            try:
                state.comparison = saved.from_dict(item.data)
            except ValueError:
                ui.notify("Questa posizione salvata è danneggiata", type="negative")
                return
            state.comparison_name = item.name
        ctx.rerender()

    async def export_png() -> None:
        if ctx.main_chart is None:
            return
        url = await ctx.main_chart.run_chart_method(
            "getDataURL",
            {"pixelRatio": 2, "backgroundColor": chart_palette()["surface"]},
            timeout=5,
        )
        content = base64.b64decode(str(url).split(",", 1)[1])
        ui.download.content(content, f"{state.ticker or 'payoff'}-grafico.png", "image/png")

    with ui.row().classes("w-full items-center gap-x-5 gap-y-2 px-2 pt-1 flex-wrap"):
        # Tempo
        with ui.row().classes("items-center gap-2 no-wrap grow min-w-[260px]"):
            ui.button(icon="pause" if playing else "play_arrow", on_click=toggle_play).props(
                "unelevated round dense color=primary"
            ).tooltip("Ferma" if playing else "Fai scorrere il tempo fino alla scadenza")
            with ui.column().classes("gap-0 grow"):
                when = date.today() + timedelta(days=round(forward))
                ui.label(
                    "Oggi"
                    if forward <= 0
                    else f"Fra {format_number(forward, 0)} gg · {when.strftime('%d/%m/%Y')}"
                ).classes("text-xs t-muted")
                throttled_slider(
                    minimum=0,
                    maximum=max(dte, 1),
                    step=1,
                    value=forward,
                    on_value=set_forward,
                ).classes("w-full").props("color=primary")

        # Confronto
        username = auth.current_username()
        options = {NO_COMPARISON: "Nessun confronto"}
        if username:
            options.update({p.position_id: p.name for p in saved.list_for(username)})
        current = next(
            (k for k, v in options.items() if k and v == state.comparison_name),
            NO_COMPARISON,
        )
        ui.select(
            options,
            value=current,
            label="Confronta con",
            on_change=lambda e: set_comparison(e.value),
        ).props("dense outlined options-dense").classes("w-[220px]")

        # Esporta
        with ui.row().classes("gap-1 no-wrap"):
            ui.button(icon="image", on_click=export_png).props("flat dense round").classes(
                "t-muted"
            ).tooltip("Scarica il grafico come immagine")
            ui.button(
                icon="picture_as_pdf", on_click=lambda: ui.navigate.to("/stampa", new_tab=True)
            ).props("flat dense round").classes("t-muted").tooltip(
                "Riepilogo stampabile / salvabile in PDF"
            )


# ---------------------------------------------------------------------------
# Posizioni salvate
# ---------------------------------------------------------------------------


def load_saved_into(ctx: PageContext, position_id: str) -> None:
    """Sostituisce la posizione della pagina con una salvata."""
    username = auth.current_username()
    item = saved.get(username, position_id) if username else None
    if item is None:
        ui.notify("Posizione non trovata", type="warning")
        return
    try:
        state = saved.from_dict(item.data)
    except ValueError:
        ui.notify("Questa posizione salvata è danneggiata", type="negative")
        return
    session.replace_position(state)
    ctx.state = state
    ui.notify(f"Aperta «{item.name}»", type="positive")
    ctx.rerender()


def saved_panel(ctx: PageContext) -> None:
    username = auth.current_username()
    if username is None:
        return
    items = saved.list_for(username)

    with ui.dialog() as dialog, ui.card().classes("sim-card w-[400px] max-w-full gap-3"):
        card_title("Salva la posizione", "bookmark_add")
        name = (
            ui.input(
                "Nome",
                value=f"{ctx.state.ticker} · {STRATEGIES[ctx.state.strategy_key].name}"
                if ctx.state.strategy_key in STRATEGIES
                else ctx.state.ticker,
            )
            .classes("w-full")
            .props("dense outlined autofocus")
        )
        ui.label(
            "Se usi un nome già salvato, la posizione con quel nome viene aggiornata."
        ).classes(FAINT)
        error = ui.label("").classes("text-xs t-loss")

        def confirm() -> None:
            problem = saved.save(username, name.value or "", ctx.state)
            if problem is not None:
                error.set_text(problem)
                return
            dialog.close()
            ui.notify("Posizione salvata", type="positive")
            ctx.rerender()

        name.on("keydown.enter", confirm)
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Annulla", on_click=dialog.close).props("flat no-caps").classes("t-muted")
            ui.button("Salva", icon="check", on_click=confirm).props("unelevated no-caps")

    async def import_file(e: events.UploadEventArguments) -> None:
        try:
            imported_name, state = saved.import_bytes(await e.file.read())
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        session.replace_position(state)
        ctx.state = state
        ui.notify(f"Importata «{imported_name}». Premi «Salva» per tenerla.", type="positive")
        ctx.rerender()

    def export_file() -> None:
        filename = f"{ctx.state.ticker or 'posizione'}-{date.today().isoformat()}.json"
        ui.download.content(saved.export_bytes(name.value or ctx.state.ticker, ctx.state), filename)

    with ui.dialog() as import_dialog, ui.card().classes("sim-card w-[420px] max-w-full gap-3"):
        card_title("Importa una posizione", "upload_file")
        ui.label(
            "Scegli un file .json esportato dal simulatore (anche da un altro computer)."
        ).classes(FAINT)
        ui.upload(on_upload=import_file, auto_upload=True, max_file_size=1_000_000).props(
            'accept=".json" flat bordered color=primary'
        ).classes("w-full")
        ui.button("Chiudi", on_click=import_dialog.close).props("flat no-caps").classes(
            "self-end t-muted"
        )

    with ui.card().classes(CARD):
        card_title(
            "Le mie posizioni",
            "bookmarks",
            subtitle=f"{len(items)} salvat{'a' if len(items) == 1 else 'e'}",
            action=("Salva", "bookmark_add", dialog.open),
        )
        with ui.row().classes("w-full gap-2 -mt-1 mb-1"):
            ui.button("Esporta file", icon="download", on_click=export_file).props(
                "outline dense no-caps color=primary"
            ).classes("text-xs px-2")
            ui.button("Importa file", icon="upload", on_click=import_dialog.open).props(
                "outline dense no-caps color=primary"
            ).classes("text-xs px-2")
        if not items:
            ui.label(
                "Nessuna posizione salvata. Costruisci una strategia e premi «Salva» "
                "per ritrovarla in seguito, anche dopo aver spento il simulatore."
            ).classes(FAINT)
            return
        with ui.column().classes("w-full gap-0"):
            for item in items[:5]:
                with ui.row().classes("w-full items-center gap-2 no-wrap py-1.5 sim-divider"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item.name).classes("text-sm t-text truncate")
                        ui.label(
                            f"{display_symbol(item.ticker)} · {item.leg_count} "
                            f"gamb{'a' if item.leg_count == 1 else 'e'}"
                        ).classes("text-[11px] t-faint")
                    ui.button(
                        icon="open_in_new",
                        on_click=lambda _, i=item.position_id: load_saved_into(ctx, i),
                    ).props("flat dense round size=sm color=primary").tooltip("Apri")
        ui.link(
            "Gestiscile tutte nel tuo account →"
            if len(items) > 5
            else "Gestisci nel tuo account →",
            "/account",
        ).classes("text-xs t-accent no-underline mt-auto pt-1")


# ---------------------------------------------------------------------------
# Costruttore di gambe
# ---------------------------------------------------------------------------


def legs_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def after(action: Any) -> None:
        action()
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title(
            "Gambe della posizione",
            "stacked_line_chart",
            subtitle="Ogni riga è un contratto o un'azione",
            action=("Aggiungi gamba", "add", lambda: after(state.add_leg)),
        )

        # Su schermi stretti la tabella scorre in orizzontale dentro la card,
        # invece di schiacciare i campi o allargare la pagina.
        with ui.column().classes("w-full gap-2 overflow-x-auto pb-1"):
            with ui.row().classes("min-w-[600px] gap-2 no-wrap sim-thead px-1"):
                ui.label("Tipo").classes("w-24")
                ui.label("Posizione").classes("w-24")
                ui.label("Strike").classes("w-24")
                ui.label("Q.tà").classes("w-20")
                ui.label("Premio").classes("w-24")
                ui.label("").classes("w-16")

            for leg in state.legs:
                is_stock = isinstance(leg, StockLeg)
                leg_id = leg.leg_id
                code = moneyness(leg, state.market.spot)
                with ui.row().classes("min-w-[600px] gap-2 no-wrap items-center"):
                    ui.select(
                        {"call": "Call", "put": "Put", "stock": "Azione"},
                        value="stock" if is_stock else leg.right,  # type: ignore[union-attr]
                        on_change=lambda e, i=leg_id: after(lambda: state.set_leg_type(i, e.value)),
                    ).classes("w-24").props("dense outlined")
                    ui.select(
                        {"long": "Long", "short": "Short"},
                        value=leg.side,
                        on_change=lambda e, i=leg_id: after(lambda: state.set_leg_side(i, e.value)),
                    ).classes("w-24").props("dense outlined")
                    commit_on_leave(
                        ui.number(
                            value=leg.entry_price if is_stock else leg.strike,  # type: ignore[union-attr]
                            step=0.5,
                            format="%.2f",
                        )
                        .classes("w-24")
                        .props("dense outlined")
                        .tooltip("Prezzo di carico dell'azione" if is_stock else "Strike"),
                        lambda v, i=leg_id: after(lambda: state.set_leg_strike(i, v)),
                    )
                    commit_on_leave(
                        ui.number(value=leg.qty, step=1, min=1, format="%.0f")
                        .classes("w-20")
                        .props("dense outlined"),
                        lambda v, i=leg_id: after(lambda: state.set_leg_qty(i, v)),
                    )

                    premium = a.entry_premiums.get(leg_id, 0.0)
                    if is_stock:
                        ui.number(value=premium, format="%.2f").classes("w-24").props(
                            "dense outlined readonly"
                        ).tooltip("Per l'azione il costo è il prezzo di carico")
                    else:
                        commit_on_leave(
                            ui.number(value=round(premium, 2), step=0.05, format="%.2f")
                            .classes("w-24")
                            .props("dense outlined")
                            .tooltip("Premio teorico. Modificalo per imporre un valore manuale."),
                            lambda v, i=leg_id: after(lambda: state.set_leg_premium(i, v)),
                        )

                    with ui.row().classes("w-16 gap-1 items-center no-wrap"):
                        ui.label(code).classes("sim-chip").style(f"color: {MONEYNESS_COLOR[code]}")
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda _, i=leg_id: after(lambda: state.remove_leg(i)),
                        ).props("flat dense round size=sm").classes("t-faint").tooltip(
                            "Rimuovi gamba"
                        )

        with ui.row().classes("w-full items-center justify-between mt-auto pt-2"):
            if state.has_manual_premiums():
                ui.button(
                    "Riporta tutti i premi al teorico",
                    icon="restart_alt",
                    on_click=lambda: after(state.reset_premiums),
                ).props("flat dense no-caps color=primary").classes("text-xs")
            else:
                ui.label("").classes("grow")
            debit = a.net_cost >= 0
            title = "Costo netto (debito)" if debit else "Credito netto incassato"
            ui.label(f"{title}: {format_signed_money(-a.net_cost, state.currency)}").classes(
                "text-sm font-semibold t-num"
            ).style(f"color: {COLOR_LOSS if debit else COLOR_PROFIT}")


# ---------------------------------------------------------------------------
# Riepilogo
# ---------------------------------------------------------------------------


def summary_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics
    with ui.card().classes(CARD):
        card_title(
            "Riepilogo della posizione",
            "insights",
            subtitle=f"{state.ticker} · {state.name} · "
            f"scade {format_expiry(state.market.days_to_expiry)}",
        )
        with ui.element("div").classes(
            "w-full grid gap-2 grid-cols-2 md:grid-cols-3 2xl:grid-cols-5"
        ):
            debit = a.net_cost >= 0
            stat(
                "Costo / credito netto",
                format_signed_money(-a.net_cost, state.currency),
                tone="loss" if debit else "profit",
                sub="esborso iniziale" if debit else "premio incassato",
                icon="account_balance_wallet",
            )
            stat(
                "Profitto massimo",
                format_signed_money(a.max_profit, state.currency),
                tone="profit",
                sub="illimitato verso l'alto" if a.profit_unbounded else "a scadenza",
                icon="trending_up",
            )
            stat(
                "Perdita massima",
                format_signed_money(a.max_loss, state.currency),
                tone="loss",
                sub="ILLIMITATA — rischio non coperto" if a.loss_unbounded else "a scadenza",
                icon="trending_down",
            )
            be_text = (
                "  ·  ".join(format_number(b, 2) for b in a.break_evens)
                if a.break_evens
                else "nessuno"
            )
            stat("Break-even", be_text, icon="adjust")
            stat(
                "Probabilità di profitto",
                format_percent(a.prob_profit, 1),
                tone="profit" if a.prob_profit >= 0.5 else "loss",
                sub="a scadenza, secondo il modello",
                icon="casino",
            )

        if a.loss_unbounded:
            with ui.row().classes(DANGER_STRIP + " mt-3"):
                ui.icon("warning", size="18px")
                ui.label(
                    "Questa posizione ha perdita potenzialmente illimitata: una gamba "
                    "venduta non è coperta da una comprata più esterna."
                ).classes("grow")


# ---------------------------------------------------------------------------
# Greche
# ---------------------------------------------------------------------------


def greeks_panel(ctx: PageContext) -> None:
    g = ctx.analytics.greeks
    with ui.card().classes(CARD):
        card_title(
            "Greche aggregate della posizione",
            "functions",
            subtitle="Somma delle greche di tutte le gambe, con segno e quantità.",
        )
        with ui.element("div").classes(
            "w-full grid gap-3 grid-cols-1 sm:grid-cols-2 xl:grid-cols-5"
        ):
            for symbol, name, attribute, unit, description in GREEK_ROWS:
                value = getattr(g, attribute)
                with ui.column().classes("gap-1 sim-stat min-w-0"):
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        ui.label(symbol).classes("t-serif text-[20px] t-accent leading-none")
                        ui.label(name).classes("sim-stat-label")
                    with ui.row().classes("items-baseline gap-1.5 no-wrap"):
                        ui.label(format_number(value, 4)).classes("sim-stat-value").style(
                            f"color: {COLOR_PROFIT if value >= 0 else COLOR_LOSS}"
                        )
                        if unit:
                            ui.label(unit).classes("text-[11px] t-muted")
                    ui.label(description).classes("text-[11px] t-faint leading-relaxed")


# ---------------------------------------------------------------------------
# Mappa di calore
# ---------------------------------------------------------------------------


def heatmap_intro_panel(ctx: PageContext) -> None:
    card_title(
        "Mappa del P&L: prezzo × tempo",
        "grid_on",
        subtitle="Ogni casella è il guadagno o la perdita per unità, se il titolo "
        "valesse quel prezzo in quel giorno (IV e tasso fermi).",
    )


# ---------------------------------------------------------------------------
# Scenario: prezzo, data e volatilità
# ---------------------------------------------------------------------------

PRICE_CHIPS = [("−10%", -0.10), ("−5%", -0.05), ("Oggi", 0.0), ("+5%", 0.05), ("+10%", 0.10)]
IV_CHIPS = [("Crollo −50%", -0.50), ("−30%", -0.30), ("Attuale", 0.0), ("+30%", 0.30)]


def _leg_label(leg: Any) -> str:
    if isinstance(leg, StockLeg):
        return f"{leg.side.title()} {format_number(leg.qty, 0)}× azione"
    return (
        f"{leg.side.title()} {format_number(leg.qty, 0)}× {leg.right} "
        f"{format_number(leg.strike, 2)}"
    )


def _chips(options: list[tuple[str, Any]], on_pick: Any, active: Any) -> None:
    with ui.row().classes("gap-1 flex-wrap"):
        for label, value in options:
            selected = active is not None and abs(value - active) < 1e-9
            ui.button(label, on_click=lambda _, v=value: on_pick(v)).props(
                "dense no-caps unelevated color=primary" if selected else "dense no-caps outline"
            ).classes("text-[11px] px-2" + ("" if selected else " t-muted"))


def scenario_panel(ctx: PageContext) -> None:
    """Che cosa succede se fra N giorni il titolo vale X e la IV è Y."""
    state = ctx.state
    a = ctx.analytics
    sc = a.scenario
    m = state.market
    dte = m.days_to_expiry
    cur = state.currency

    def set_price(value: Any) -> None:
        if value:
            state.target = float(value)
            ctx.rerender()

    def set_days(value: float) -> None:
        state.days_forward = min(max(float(value), 0.0), dte)
        ctx.rerender()

    def set_iv(value: float) -> None:
        state.iv_sim = max(float(value), 0.01)
        ctx.rerender()

    def reset() -> None:
        state.target, state.days_forward, state.iv_sim = m.spot, 0.0, m.iv
        ctx.rerender()

    card_title(
        "Simulatore di scenari",
        "science",
        subtitle="Scegli dove sarà il titolo, fra quanti giorni e con quale volatilità: "
        "vedi il P&L e da dove viene.",
    )

    with ui.row().classes("w-full gap-8 no-wrap max-lg:flex-wrap items-start"):
        # --- Comandi -------------------------------------------------------
        with ui.column().classes("grow basis-0 min-w-[280px] gap-4"):
            with ui.column().classes("w-full gap-1"):
                move = sc.price / m.spot - 1
                ui.label(
                    f"Prezzo del titolo: {format_money(sc.price, cur)} "
                    f"({'+' if move >= 0 else ''}{format_percent(move, 1)} da oggi)"
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=round(a.chart_low, 1),
                    maximum=round(a.chart_high, 1),
                    step=0.5,
                    value=min(max(sc.price, a.chart_low), a.chart_high),
                    on_value=set_price,
                ).classes("w-full")
                _chips(
                    [(label, round(m.spot * (1 + d), 2)) for label, d in PRICE_CHIPS],
                    set_price,
                    round(sc.price, 2),
                )

            with ui.column().classes("w-full gap-1"):
                when = date.today() + timedelta(days=round(sc.days))
                ui.label(
                    "Quando: oggi"
                    if sc.days <= 0
                    else f"Quando: fra {format_number(sc.days, 0)} gg "
                    f"({when.strftime('%d/%m/%Y')})" + (" · a scadenza" if sc.days >= dte else "")
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=0, maximum=max(dte, 1), step=1, value=sc.days, on_value=set_days
                ).classes("w-full")
                _chips(
                    [
                        ("Oggi", 0.0),
                        ("1 settimana", min(7.0, dte)),
                        ("Metà", round(dte / 2)),
                        ("Scadenza", dte),
                    ],
                    set_days,
                    sc.days,
                )

            with ui.column().classes("w-full gap-1"):
                change = sc.iv / m.iv - 1 if m.iv > 0 else 0.0
                ui.label(
                    f"Volatilità implicita: {format_percent(sc.iv, 1)}"
                    + (
                        f" ({'+' if change >= 0 else ''}{format_percent(change, 0)} "
                        f"rispetto a oggi)"
                        if abs(change) > 1e-9
                        else " (come oggi)"
                    )
                ).classes("text-sm font-medium t-text")
                throttled_slider(
                    minimum=1,
                    maximum=150,
                    step=1,
                    value=round(sc.iv * 100),
                    on_value=lambda v: set_iv(v / 100),
                ).classes("w-full")
                _chips(
                    [(label, round(m.iv * (1 + d), 6)) for label, d in IV_CHIPS],
                    set_iv,
                    round(sc.iv, 6),
                )
                ui.label(
                    "Il «vol crush» è il crollo della IV dopo un evento atteso, tipicamente "
                    "gli utili trimestrali: chi ha comprato opzioni perde anche se il prezzo "
                    "si muove nella direzione giusta."
                ).classes(FAINT)

            ui.button("Azzera scenario", icon="restart_alt", on_click=reset).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs self-start")

        # --- Risultato -----------------------------------------------------
        with ui.column().classes("grow basis-0 min-w-[300px] gap-3"):
            sizing = state.sizing
            units = sizing.contract_multiplier * sizing.packages
            stat(
                "P&L nello scenario",
                format_signed_money(sc.pl, cur),
                tone="profit" if sc.pl >= 0 else "loss",
                sub=f"per azione · {format_signed_money(sc.pl * units, cur)} sulla posizione "
                f"reale ({format_number(units, 0)} azioni)",
                icon="flag",
            )

            ui.label("Da dove viene").classes("sim-stat-label mt-1")
            parts = [
                ("Se chiudessi oggi", sc.pl_today, "today"),
                ("Movimento del prezzo", sc.effect_price, "show_chart"),
                ("Tempo che passa (theta)", sc.effect_time, "hourglass_bottom"),
                ("Cambio di volatilità (vega)", sc.effect_vol, "waves"),
            ]
            largest = max((abs(v) for _, v, _ in parts), default=1.0) or 1.0
            with ui.column().classes("w-full gap-1"):
                for label, value, icon in parts:
                    color = COLOR_PROFIT if value >= 0 else COLOR_LOSS
                    with ui.row().classes("w-full items-center gap-2 no-wrap"):
                        ui.icon(icon, size="16px").classes("t-muted")
                        ui.label(label).classes("text-xs t-text2 w-[170px] shrink-0")
                        with (
                            ui.element("div")
                            .classes("grow h-2 rounded-full")
                            .style("background: var(--surface-2)")
                        ):
                            ui.element("div").classes("h-2 rounded-full").style(
                                f"width: {abs(value) / largest * 100:.1f}%; background: {color}"
                            )
                        ui.label(format_signed_money(value, cur)).classes(
                            "text-xs font-semibold t-num w-[78px] text-right"
                        ).style(f"color: {color}")
                with ui.row().classes("w-full items-center gap-2 no-wrap sim-divider pt-1"):
                    ui.label("= P&L nello scenario").classes("text-xs font-semibold t-text grow")
                    ui.label(format_signed_money(sc.pl, cur)).classes(
                        "text-xs font-semibold t-num w-[78px] text-right"
                    ).style(f"color: {COLOR_PROFIT if sc.pl >= 0 else COLOR_LOSS}")

            with ui.row().classes("w-full gap-2 no-wrap sim-thead mt-2 px-1"):
                ui.label("Gamba").classes("grow")
                ui.label("Pagato").classes("w-20 text-right")
                ui.label("Varrà").classes("w-20 text-right")
                ui.label("P&L").classes("w-24 text-right")
            legs = {leg.leg_id: leg for leg in state.legs}
            for row in sc.legs:
                with ui.row().classes(
                    "w-full gap-2 no-wrap text-xs t-text2 t-num py-1.5 sim-divider px-1"
                ):
                    ui.label(_leg_label(legs[row.leg_id])).classes("grow")
                    ui.label(format_number(row.entry, 2)).classes("w-20 text-right")
                    ui.label(format_number(row.value, 2)).classes("w-20 text-right")
                    ui.label(format_signed_money(row.pl, cur)).classes(
                        "w-24 text-right font-semibold"
                    ).style(f"color: {COLOR_PROFIT if row.pl >= 0 else COLOR_LOSS}")

    _scenario_matrix(state, sc)


def _scenario_matrix(state: PositionState, sc: Scenario) -> None:
    m = state.market
    cur = state.currency
    largest = max((abs(v) for row in sc.matrix for v in row), default=1.0) or 1.0
    when = "oggi" if sc.days <= 0 else f"fra {format_number(sc.days, 0)} gg"
    ui.label(f"Matrice degli scenari · P&L {when}").classes("sim-card-title mt-6")
    ui.label(
        "Ogni casella combina una variazione del prezzo (colonne) e della IV (righe). "
        "Utile per vedere a colpo d'occhio se la posizione teme di più il prezzo o la "
        "volatilità."
    ).classes(FAINT)
    with ui.column().classes("w-full gap-1 overflow-x-auto mt-2"):
        with ui.row().classes("min-w-[620px] w-full no-wrap gap-1"):
            ui.label("IV \\ prezzo").classes("w-[96px] sim-thead self-end")
            for move in MATRIX_PRICE_MOVES:
                with ui.column().classes("grow basis-0 gap-0 items-center"):
                    ui.label(
                        "oggi"
                        if move == 0
                        else f"{'+' if move > 0 else ''}{format_percent(move, 1)}"
                    ).classes("sim-thead")
                    ui.label(format_number(m.spot * (1 + move), 2)).classes("text-[11px] t-faint")
        for iv_move, row in zip(MATRIX_IV_MOVES, sc.matrix, strict=True):
            with ui.row().classes("min-w-[620px] w-full no-wrap gap-1"):
                with ui.column().classes("w-[96px] gap-0 justify-center"):
                    ui.label(
                        "IV attuale"
                        if iv_move == 0
                        else f"IV {'+' if iv_move > 0 else ''}{format_percent(iv_move, 0)}"
                    ).classes("text-xs t-text2")
                    ui.label(format_percent(m.iv * (1 + iv_move), 1)).classes("text-[11px] t-faint")
                for move, value in zip(MATRIX_PRICE_MOVES, row, strict=True):
                    strength = 12 + 58 * min(abs(value) / largest, 1.0)
                    color = "var(--profit)" if value >= 0 else "var(--loss)"
                    centre = move == 0 and iv_move == 0
                    ui.label(format_signed_money(value, cur)).classes(
                        "grow basis-0 text-center text-xs font-semibold t-num py-2 "
                        "rounded-md t-text" + (" ring-2 ring-[var(--accent)]" if centre else "")
                    ).style(f"background: color-mix(in srgb, {color} {strength:.0f}%, transparent)")


# ---------------------------------------------------------------------------
# Costo dell'operazione
# ---------------------------------------------------------------------------


def cost_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_sizing(*, packages: Any = None, contract_multiplier: Any = None) -> None:
        sizing = state.sizing
        if packages:
            sizing = replace(sizing, packages=max(1, int(packages)))
        if contract_multiplier:
            sizing = replace(sizing, contract_multiplier=max(1.0, float(contract_multiplier)))
        if sizing == state.sizing:
            return
        state.sizing = sizing
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title("Costo dell'operazione", "receipt_long")
        ui.label(
            "Traduce i prezzi teorici in esborso reale. Ogni contratto controlla "
            f"{format_number(state.sizing.contract_multiplier, 0)} unità di sottostante: "
            "il costo di una gamba è premio × moltiplicatore × contratti × pacchetti."
        ).classes(FAINT)

        with ui.row().classes("w-full gap-2 no-wrap mt-2"):
            commit_on_leave(
                ui.number(
                    "Pacchetti (repliche)",
                    value=state.sizing.packages,
                    step=1,
                    min=1,
                    format="%.0f",
                )
                .classes("grow")
                .props("dense outlined"),
                lambda v: set_sizing(packages=v),
            )
            commit_on_leave(
                ui.number(
                    "Moltiplicatore contratto",
                    value=state.sizing.contract_multiplier,
                    step=1,
                    min=1,
                    format="%.0f",
                )
                .classes("grow")
                .props("dense outlined suffix=az."),
                lambda v: set_sizing(contract_multiplier=v),
            )

        with ui.row().classes("w-full gap-2 no-wrap sim-thead mt-4 px-1"):
            ui.label("Gamba").classes("grow")
            ui.label("Prezzo unit.").classes("w-24 text-right")
            ui.label("Unità tot.").classes("w-24 text-right")
            ui.label("Flusso").classes("w-28 text-right")

        for leg_cost in a.cost.legs:
            leg = leg_cost.resolved.leg
            short = leg.side == "short"
            if isinstance(leg, StockLeg):
                label = f"{leg.side.title()} Azione @ {format_number(leg.entry_price, 0)}"
            else:
                label = f"{leg.side.title()} {leg.right.title()} {format_number(leg.strike, 0)}"
            with ui.row().classes("w-full gap-2 no-wrap text-xs t-text2 t-num py-2 sim-divider"):
                ui.label(f"{label} ×{format_number(leg.qty, 0)}").classes("grow")
                ui.label(format_money(leg_cost.unit_price, state.currency)).classes(
                    "w-24 text-right"
                )
                ui.label(format_number(leg_cost.units, 0)).classes("w-24 text-right")
                ui.label(
                    format_signed_money(
                        leg_cost.gross if short else -leg_cost.gross, state.currency
                    )
                ).classes("w-28 text-right font-semibold").style(
                    f"color: {COLOR_PROFIT if short else COLOR_LOSS}"
                )

        with ui.row().classes("w-full gap-2 flex-wrap mt-3"):
            stat(
                "Esborso (premi/azioni pagati)",
                format_signed_money(-a.cost.total_outflow, state.currency),
                tone="loss",
            )
            stat(
                "Incasso (premi venduti)",
                format_signed_money(a.cost.total_inflow, state.currency),
                tone="profit",
            )
            debit = a.cost.net >= 0
            packages = state.sizing.packages
            stat(
                "Costo netto totale" if debit else "Credito netto totale",
                format_signed_money(-a.cost.net, state.currency),
                tone="loss" if debit else "profit",
                sub=f"per {packages} pacchett{'o' if packages == 1 else 'i'}",
            )

        if a.cost.net < 0:
            ui.label(
                "Le posizioni a credito richiedono in genere un margine presso il "
                "broker, non mostrato qui."
            ).classes(FAINT)
