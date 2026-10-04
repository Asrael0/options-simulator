"""Compact builders for the engine tests.

Not a test: a toolbox FOR the tests. Creating an ``OptionSpec`` takes seven
arguments; tests change one at a time. These functions allow writing
``spec(strike=110)`` to mean "everything as usual, but with strike 110".

The base parameters are those of the reference table:
S = 100, K = 100, T = 30 days, r = 4%, IV = 30%, no dividend.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Any

from options_simulator.pricing import (
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
    """Standard market parameters, with the requested changes."""
    return replace(BASE_MARKET, **overrides)


def spec(**overrides: Any) -> OptionSpec:
    """Standard option specification, with the requested changes."""
    return replace(BASE_SPEC, **overrides)


def _next_id() -> str:
    """Sequential identifier for a test leg."""
    return f"leg-{next(_ids)}"


def option(
    right: Right,
    side: Side,
    strike: float,
    qty: float = 1.0,
    iv_override: float | None = None,
) -> OptionLeg:
    """An option leg whose premium comes from the model."""
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
    """An option leg with a manual premium."""
    return OptionLeg(
        leg_id=_next_id(),
        side=side,
        qty=qty,
        right=right,
        strike=strike,
        premium=ManualPremium(premium),
    )


def stock(side: Side, entry_price: float, qty: float = 1.0) -> StockLeg:
    """A stock leg."""
    return StockLeg(leg_id=_next_id(), side=side, qty=qty, entry_price=entry_price)
