"""Types of the pricing engine.

Nothing is computed here. This module only defines the project's *vocabulary*:
what a leg is, what market parameters are, what the Greeks are. Every other
module imports from here, so they all speak the same language.

UNIT CONVENTIONS — read before touching any formula.

1. Rates and volatilities are ALWAYS decimals, never percentages.
   IV of 30% => 0.30. Rate of 4% => 0.04. Converting to and from percentages is
   solely the presentation layer's job.

2. The engine works PER UNIT OF UNDERLYING. ``qty`` is a pure multiplier. The
   contract multiplier (100 shares) and the number of packages live only in
   ``trade_cost()``, in the money layer.

3. Greeks carry their unit in the name. ``theta_per_day`` is in currency per
   day, not per year; ``vega_per_point`` is per +1 IV point (i.e. +0.01
   decimal), not per +1.00.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["long", "short"]
Right = Literal["call", "put"]
ExerciseStyle = Literal["european", "american"]
Resolution = Literal["full", "curve"]

STEPS_BY_RESOLUTION: dict[Resolution, int] = {"full": 140, "curve": 70}


# ---------------------------------------------------------------------------
# Where the entry premium comes from
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TheoreticalPremium:
    """The engine computes the premium from the market parameters."""


@dataclass(frozen=True, slots=True)
class ManualPremium:
    """The user set the premium by hand."""

    value: float


PremiumSource = TheoreticalPremium | ManualPremium


# ---------------------------------------------------------------------------
# Position legs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OptionLeg:
    """An option leg."""

    leg_id: str
    side: Side
    qty: float
    right: Right
    strike: float

    premium: PremiumSource = TheoreticalPremium()

    iv_override: float | None = None


@dataclass(frozen=True, slots=True)
class StockLeg:
    """A stock leg.

    ``entry_price`` is the purchase price, NOT a strike: it enters no pricing
    formula and only serves as the cost basis for the P&L.
    """

    leg_id: str
    side: Side
    qty: float
    entry_price: float


Leg = OptionLeg | StockLeg


# ---------------------------------------------------------------------------
# Market, Greeks, pricing specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarketParams:
    """Market parameters observable at a given instant."""

    spot: float
    days_to_expiry: float
    risk_free_rate: float
    iv: float
    dividend_yield: float = 0.0


@dataclass(frozen=True, slots=True)
class Greeks:
    """Sensitivities of an option or a position."""

    delta: float
    gamma: float
    theta_per_day: float
    vega_per_point: float
    rho_per_point: float


@dataclass(frozen=True, slots=True)
class PricedOption:
    """Price and Greeks of a single option."""

    price: float
    delta: float
    gamma: float
    theta_per_day: float
    vega_per_point: float
    rho_per_point: float

    def greeks(self) -> Greeks:
        """Extract the Greeks only, dropping the price."""
        return Greeks(
            delta=self.delta,
            gamma=self.gamma,
            theta_per_day=self.theta_per_day,
            vega_per_point=self.vega_per_point,
            rho_per_point=self.rho_per_point,
        )


@dataclass(frozen=True, slots=True)
class OptionSpec:
    """Complete, self-contained description of an option to price."""

    spot: float
    strike: float
    days_to_expiry: float
    risk_free_rate: float
    iv: float
    right: Right
    dividend_yield: float = 0.0


@dataclass(frozen=True, slots=True)
class Sizing:
    """Money sizing of the trade."""

    contract_multiplier: float = 100.0
    packages: int = 1


@dataclass(frozen=True, slots=True)
class ResolvedLeg:
    """A leg whose entry premium has already been resolved to a number."""

    leg: Leg
    entry_premium: float
    signed_qty: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DAYS_PER_YEAR = 365.0


def years_from_days(days: float) -> float:
    """Days -> years. Negative expiries count as zero, not negative time."""
    return max(days, 0.0) / DAYS_PER_YEAR


def effective_iv(leg: OptionLeg, market: MarketParams) -> float:
    """The leg's IV: its override if set, otherwise the global one."""
    return leg.iv_override if leg.iv_override is not None else market.iv


def spec_for_leg(leg: OptionLeg, market: MarketParams) -> OptionSpec:
    """Build a leg's ``OptionSpec`` from the market parameters."""
    return OptionSpec(
        spot=market.spot,
        strike=leg.strike,
        days_to_expiry=market.days_to_expiry,
        risk_free_rate=market.risk_free_rate,
        iv=effective_iv(leg, market),
        dividend_yield=market.dividend_yield,
        right=leg.right,
    )
