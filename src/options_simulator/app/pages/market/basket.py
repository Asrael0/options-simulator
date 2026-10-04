"""Riquadro «Le tue scelte»: le opzioni scelte, da aprire nel simulatore o nel portafoglio."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from ... import auth, portfolio, session
from ...formatting import (
    format_date,
    format_money,
    format_number,
    format_percent,
    format_signed_money,
)
from ...i18n import tr
from ...market_data import (
    BasketLeg,
    position_from_basket,
)
from ...tickers import display_symbol
from ...widgets import (
    CARD,
    COLOR_LOSS,
    COLOR_PROFIT,
    FAINT,
    card_title,
)
from .view import CONTRACT_MULTIPLIER, MarketView


def render_basket(view: MarketView, refresh: Any) -> None:
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
                tr("Apri nel portafoglio virtuale"),
                "account_balance_wallet",
                subtitle=tr(
                    "{display_symbol} · scadenza {strftime}",
                    display_symbol=display_symbol(chain.ticker),
                    strftime=format_date(expiry),
                ),
            )
            ui.label(
                tr(
                    (
                        "Pagheresti {money} (prezzi reali, {contract_multiplier} azioni per "
                        "contratto). Nessun soldo vero: il simulatore ricorda solo i prezzi "
                        "e la previsione del modello, per confrontarli poi con quello che "
                        "succede."
                    )
                    if cost >= 0
                    else (
                        "Incasseresti {money} (prezzi reali, {contract_multiplier} azioni per "
                        "contratto). Nessun soldo vero: il simulatore ricorda solo i prezzi "
                        "e la previsione del modello, per confrontarli poi con quello che "
                        "succede."
                    ),
                    money=format_money(abs(cost)),
                    contract_multiplier=CONTRACT_MULTIPLIER,
                )
            ).classes("text-sm t-muted")
            note = (
                ui.textarea(
                    tr("La tua previsione (facoltativa)"),
                    placeholder=tr("es. credo che salga sopra 340 prima della scadenza"),
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
                ui.notify(tr("Posizione aperta nel portafoglio virtuale"), type="positive")
                ui.navigate.to("/portafoglio")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(tr("Annulla"), on_click=dialog.close).props("flat no-caps").classes(
                    "t-muted"
                )
                ui.button(tr("Apri la posizione"), icon="check", on_click=confirm).props(
                    "unelevated no-caps"
                )
        dialog.open()

    with ui.card().classes(CARD):
        expiry = info.market_expiry
        card_title(
            tr("Le tue scelte"),
            "shopping_cart",
            subtitle=(
                tr(
                    "{display_symbol} · scadenza {strftime}",
                    display_symbol=display_symbol(info.market_ticker),
                    strftime=format_date(expiry),
                )
                if basket and expiry
                else tr("Clicca un'opzione nella catena")
            ),
        )
        if not basket:
            ui.label(
                tr(
                    "Qui si raccolgono le opzioni che compri o vendi dalla catena. Tutte "
                    "devono avere la stessa scadenza: cambiando scadenza la selezione "
                    "riparte da capo."
                )
            ).classes(FAINT)
            return

        net = 0.0
        for index, leg in enumerate(basket):
            sign = 1 if leg.side == "long" else -1
            net += sign * leg.premium * leg.qty
            with ui.row().classes("w-full items-center gap-2 no-wrap py-2 sim-divider"):
                ui.label(tr("L") if leg.side == "long" else tr("S")).classes("sim-chip").style(
                    f"color: {COLOR_PROFIT if leg.side == 'long' else COLOR_LOSS}"
                )
                with ui.column().classes("gap-0 grow min-w-0"):
                    ui.label(
                        tr(
                            "{x} {right} {strike}",
                            x="Long" if leg.side == "long" else "Short",
                            right=leg.right,
                            strike=format_number(leg.strike, 2),
                        )
                    ).classes("text-sm t-text")
                    ui.label(
                        tr("a {premium}", premium=format_number(leg.premium, 2))
                        + (tr(" · IV {iv}", iv=format_percent(leg.iv, 1)) if leg.iv else "")
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
            ui.label(tr("Costo netto (debito)") if debit else tr("Credito netto")).classes(
                "text-xs t-muted"
            )
            ui.label(format_signed_money(-net)).classes("text-base font-semibold t-num").style(
                f"color: {COLOR_LOSS if debit else COLOR_PROFIT}"
            )
        ui.label(
            tr(
                "Per azione. Un contratto vale {contract_multiplier} azioni: "
                "{signed_money} per contratto.",
                contract_multiplier=CONTRACT_MULTIPLIER,
                signed_money=format_signed_money(-net * CONTRACT_MULTIPLIER),
            )
        ).classes(FAINT)

        ui.button(
            tr("Apri nel portafoglio"), icon="account_balance_wallet", on_click=open_in_portfolio
        ).props("unelevated no-caps").classes("w-full py-2 mt-2").tooltip(
            tr("Registra la posizione ai prezzi veri e seguila nei prossimi giorni")
        )
        ui.button(
            tr("Studia nel simulatore"), icon="candlestick_chart", on_click=open_in_simulator
        ).props("outline no-caps color=primary").classes("w-full py-2")
        ui.button(tr("Svuota"), icon="delete_outline", on_click=clear).props(
            "flat dense no-caps"
        ).classes("w-full t-muted text-xs")
        ui.label(
            tr(
                "Nel simulatore spot, giorni, IV, tasso e dividendo vengono dal mercato "
                "e i premi pagati sono quelli reali. Sostituisce la posizione aperta: "
                "salvala prima, se ti serve."
            )
        ).classes(FAINT)
