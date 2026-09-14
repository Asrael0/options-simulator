"""Costruttori compatti per i test del motore.

--- COSA FA QUESTO FILE ---
Non è un test: è una cassetta degli attrezzi PER i test. Creare un `OptionSpec`
richiede sette argomenti; nei test se ne cambia uno solo alla volta. Queste
funzioni permettono di scrivere `spec(strike=110)` intendendo "tutto come al
solito, ma con strike 110".

I parametri base sono quelli della tabella di riferimento:
S = 100, K = 100, T = 30 giorni, r = 4%, IV = 30%, nessun dividendo.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Any

from simulatore_opzioni_python.pricing import (
    ManualPremium,
    MarketParams,
    OptionLeg,
    OptionSpec,
    Right,
    Side,
    StockLeg,
)

BASE_MARKET = MarketParams(
    spot=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    dividend_yield=0.0,
)

BASE_SPEC = OptionSpec(
    spot=100.0,
    strike=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    right="call",
    dividend_yield=0.0,
)

_ids = itertools.count(1)


def market(**overrides: Any) -> MarketParams:
    """Parametri di mercato standard, con le modifiche richieste."""
    return replace(BASE_MARKET, **overrides)


def spec(**overrides: Any) -> OptionSpec:
    """Specifica standard di un'opzione, con le modifiche richieste."""
    return replace(BASE_SPEC, **overrides)


def _next_id() -> str:
    """Identificatore progressivo per una gamba di test."""
    return f"leg-{next(_ids)}"


def option(
    right: Right,
    side: Side,
    strike: float,
    qty: float = 1.0,
    iv_override: float | None = None,
) -> OptionLeg:
    """Una gamba opzione col premio calcolato dal modello."""
    return OptionLeg(
        leg_id=_next_id(),
        side=side,
        qty=qty,
        right=right,
        strike=strike,
        iv_override=iv_override,
    )


def option_at_premium(
    right: Right, side: Side, strike: float, premium: float, qty: float = 1.0
) -> OptionLeg:
    """Una gamba opzione con premio imposto a mano."""
    return OptionLeg(
        leg_id=_next_id(),
        side=side,
        qty=qty,
        right=right,
        strike=strike,
        premium=ManualPremium(premium),
    )


def stock(side: Side, entry_price: float, qty: float = 1.0) -> StockLeg:
    """Una gamba azionaria."""
    return StockLeg(leg_id=_next_id(), side=side, qty=qty, entry_price=entry_price)
