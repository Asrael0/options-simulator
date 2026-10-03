"""Pannelli dell'interfaccia.

--- COSA FA QUESTO FILE ---
Contiene gli otto blocchi visivi dell'applicazione: mercato, strategie, gambe,
riepilogo, greche, vol crush, scenario, costi. Ogni pannello è una funzione che
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
from .formatting import format_money, format_number, format_percent, format_signed_money
from .strategies import STRATEGIES
from .theme import chart_palette
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
            commit_on_leave(
                ui.input("Ticker", value=state.ticker).classes("grow").props("dense outlined"),
                lambda v: _set_text(ctx, "ticker", v),
            )
            commit_on_leave(
                ui.input("Nome", value=state.name).classes("grow").props("dense outlined"),
                lambda v: _set_text(ctx, "name", v),
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
            .props("dense outlined suffix=gg"),
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


def _set_text(ctx: PageContext, attribute: str, value: str) -> None:
    """Ticker e nome non entrano in nessun calcolo: nessun ricalcolo."""
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
        ui.select(
            {key: s.name for key, s in STRATEGIES.items()},
            value=state.strategy_key,
            on_change=lambda e: apply(e.value),
        ).classes("w-full").props("dense outlined")
        ui.label(STRATEGIES[state.strategy_key].description).classes(FAINT)

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
                            f"{item.ticker} · {item.leg_count} "
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
        ).classes("text-xs t-accent no-underline mt-1")


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

        with ui.row().classes("w-full items-center justify-between mt-2"):
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
            "Riepilogo della posizione", "insights", subtitle=f"{state.ticker} · {state.name}"
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
# Vol crush
# ---------------------------------------------------------------------------


def vol_crush_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_iv_sim(value: float) -> None:
        state.iv_sim = value / 100
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title("Simulatore di vol crush", "waves", subtitle="IV indipendente dal resto")
        ui.label(
            "Sposta solo la volatilità implicita tenendo fermo tutto il resto: spot, "
            "giorni, tasso. È l'effetto isolato della vega. Un calo netto di IV dopo "
            "un evento, tipicamente gli earnings, è il classico vol crush."
        ).classes(FAINT)
        ui.label(f"IV simulata: {format_percent(state.iv_sim, 1)}").classes(MUTED + " mt-2")
        throttled_slider(
            minimum=1,
            maximum=150,
            step=1,
            value=state.iv_sim * 100,
            on_value=set_iv_sim,
        ).classes("w-full")
        with ui.row().classes("w-full gap-2 flex-wrap mt-1"):
            stat(
                f"Valore oggi @ IV {format_percent(state.market.iv, 0)}",
                format_signed_money(a.value_now_current_iv, state.currency),
            )
            stat(
                f"Valore oggi @ IV {format_percent(state.iv_sim, 0)}",
                format_signed_money(a.value_now_sim_iv, state.currency),
            )
            iv_delta = format_number((state.iv_sim - state.market.iv) * 100, 1)
            stat(
                "Effetto vega",
                format_signed_money(a.vol_crush_effect, state.currency),
                tone="profit" if a.vol_crush_effect >= 0 else "loss",
                sub=f"per ΔIV di {iv_delta} punti",
            )


# ---------------------------------------------------------------------------
# Scenario a scadenza
# ---------------------------------------------------------------------------


def scenario_panel(ctx: PageContext) -> None:
    state = ctx.state
    a = ctx.analytics

    def set_target(value: Any) -> None:
        if value is None:
            return
        state.target = float(value)
        ctx.rerender()

    with ui.card().classes(CARD):
        card_title("Scenario a scadenza", "flag")
        ui.label(
            "Inserisci un prezzo-target del sottostante a scadenza e ottieni il P&L "
            "esatto su tutte le gambe."
        ).classes(FAINT)
        commit_on_leave(
            ui.number("Prezzo-target", value=state.target, step=0.5, format="%.2f")
            .classes("w-full mt-2")
            .props("dense outlined suffix=$"),
            set_target,
        )
        throttled_slider(
            minimum=round(a.chart_low, 1),
            maximum=round(a.chart_high, 1),
            step=0.5,
            value=min(max(state.target, a.chart_low), a.chart_high),
            on_value=set_target,
        ).classes("w-full")

        with ui.row().classes("w-full gap-2 mt-1"):
            stat(
                f"P&L a scadenza @ {format_money(state.target, state.currency)}",
                format_signed_money(a.scenario_pl, state.currency),
                tone="profit" if a.scenario_pl >= 0 else "loss",
                sub="in profitto" if a.scenario_pl >= 0 else "in perdita",
            )

        with ui.row().classes("w-full gap-2 no-wrap sim-thead mt-4 px-1"):
            ui.label("Gamba").classes("grow")
            ui.label("Payoff").classes("w-24 text-right")
            ui.label("Premio").classes("w-24 text-right")
            ui.label("P&L gamba").classes("w-28 text-right")

        for leg in state.legs:
            premium = a.entry_premiums.get(leg.leg_id, 0.0)
            if isinstance(leg, StockLeg):
                payoff = state.target
                label = (
                    f"{leg.side.title()} {format_number(leg.qty, 0)}× Azione @ "
                    f"{format_number(leg.entry_price, 0)}"
                )
            else:
                payoff = (
                    max(state.target - leg.strike, 0.0)
                    if leg.right == "call"
                    else max(leg.strike - state.target, 0.0)
                )
                label = (
                    f"{leg.side.title()} {format_number(leg.qty, 0)}× "
                    f"{leg.right.title()} {format_number(leg.strike, 0)}"
                )
            sign = 1.0 if leg.side == "long" else -1.0
            pl = sign * (payoff - premium) * leg.qty
            with ui.row().classes("w-full gap-2 no-wrap text-xs t-text2 t-num py-2 sim-divider"):
                ui.label(label).classes("grow")
                ui.label(format_money(payoff, state.currency)).classes("w-24 text-right")
                ui.label(format_money(premium, state.currency)).classes("w-24 text-right")
                ui.label(format_signed_money(pl, state.currency)).classes(
                    "w-28 text-right font-semibold"
                ).style(f"color: {COLOR_PROFIT if pl >= 0 else COLOR_LOSS}")


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
