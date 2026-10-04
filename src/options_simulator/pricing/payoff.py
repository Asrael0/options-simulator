"""Multi-leg P&L: payoff at expiry, current value, break-evens, extremes.

The other modules price ONE option at a time. This one works on the whole
POSITION: several legs together, with their signs and quantities.

It answers four questions:
  - what do I gain or lose if the stock is at X at expiry?  (``pl_at_expiry``)
  - at what price do I break even?                          (``break_evens``)
  - what is the most I can gain or lose?                    (``payoff_bounds``)
  - how much real money does opening it take?               (``trade_cost``)

DESIGN CHOICE — the entry premium is an INPUT, never recomputed.

In the original prototype the premium was repriced at the current parameters on
every access: moving the spot slider also changed the cost "already paid", so
the "value today" curve always crossed zero at spot and the break-evens slid
with the slider. Here ``resolve_legs()`` resolves the premiums ONCE against an
explicit ``MarketParams``. Passing the entry snapshot gives the correct
behaviour; passing the current parameters reproduces the prototype. The
decision lives outside the engine.

ANALYTICAL BREAK-EVENS — the payoff at expiry is piecewise linear, with corners
only at the strikes. Break-evens are solved in closed form segment by segment,
not by sampling: the P&L at a break-even is exactly 0, not "0 within grid
error".
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Literal

from .greeks import price_option
from .merton import JumpParams, merton_probability_below
from .normal import norm_cdf
from .types import (
    ExerciseStyle,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    Resolution,
    ResolvedLeg,
    Sizing,
    StockLeg,
    spec_for_leg,
    years_from_days,
)

_TOL = 1e-9
_DEDUPE_TOL = 1e-7


# ---------------------------------------------------------------------------
# Resolving entry premiums
# ---------------------------------------------------------------------------


def leg_entry_premium(
    leg: Leg,
    entry_market: MarketParams,
    exercise: ExerciseStyle,
    jumps: JumpParams | None = None,
) -> float:
    """Entry premium of a leg, per unit of underlying."""
    match leg:
        case StockLeg(entry_price=price):
            return price
        case OptionLeg(premium=ManualPremium(value=value)):
            return value
        case OptionLeg():
            return price_option(spec_for_leg(leg, entry_market), exercise, "full", jumps)


def resolve_legs(
    legs: list[Leg],
    entry_market: MarketParams,
    exercise: ExerciseStyle,
    jumps: JumpParams | None = None,
) -> list[ResolvedLeg]:
    """Freeze the entry premiums and apply the position sign.

    From here on the engine never reprices the entry cost.
    """
    return [
        ResolvedLeg(
            leg=leg,
            entry_premium=leg_entry_premium(leg, entry_market, exercise, jumps),
            signed_qty=leg.qty if leg.side == "long" else -leg.qty,
        )
        for leg in legs
    ]


# ---------------------------------------------------------------------------
# Payoff at expiry
# ---------------------------------------------------------------------------


def intrinsic_at_expiry(leg: Leg, final_spot: float) -> float:
    """Gross value of a leg at expiry, per unit of underlying.

    For an option it is the intrinsic value; for stock it is the price itself.
    """
    match leg:
        case StockLeg():
            return final_spot
        case OptionLeg(right="call", strike=strike):
            return max(final_spot - strike, 0.0)
        case OptionLeg(strike=strike):
            return max(strike - final_spot, 0.0)


def pl_at_expiry(legs: list[ResolvedLeg], final_spot: float) -> float:
    """Total P&L at expiry for a final underlying price."""
    return sum(
        r.signed_qty * (intrinsic_at_expiry(r.leg, final_spot) - r.entry_premium) for r in legs
    )


def pl_at_market(
    legs: list[ResolvedLeg],
    market: MarketParams,
    exercise: ExerciseStyle,
    resolution: Resolution = "full",
    jumps: JumpParams | None = None,
) -> float:
    """P&L at the given market: current value minus entry cost.

    It is the "value today" curve of the payoff diagram.
    """
    total = 0.0
    for r in legs:
        match r.leg:
            case StockLeg():
                value = market.spot
            case OptionLeg() as opt:
                value = price_option(spec_for_leg(opt, market), exercise, resolution, jumps)
        total += r.signed_qty * (value - r.entry_premium)
    return total


def _slope_at_expiry(legs: list[ResolvedLeg], final_spot: float) -> float:
    """Right derivative of the P&L at expiry with respect to the underlying price.

    It is constant on each segment between consecutive strikes, so evaluating it
    at the left end gives the slope of the whole segment.
    """
    slope = 0.0
    for r in legs:
        match r.leg:
            case StockLeg():
                slope += r.signed_qty
            case OptionLeg(right="call", strike=strike):
                if final_spot >= strike:
                    slope += r.signed_qty
            case OptionLeg(strike=strike):
                if final_spot < strike:
                    slope -= r.signed_qty
    return slope


def _sorted_strikes(legs: list[ResolvedLeg]) -> list[float]:
    """Distinct, sorted strikes of the option legs only."""
    strikes = {
        r.leg.strike
        for r in legs
        if isinstance(r.leg, OptionLeg) and math.isfinite(r.leg.strike) and r.leg.strike > 0.0
    }
    return sorted(strikes)


def _dedupe(values: list[float]) -> list[float]:
    """Remove duplicates from a sorted list, within tolerance."""
    out: list[float] = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > _DEDUPE_TOL:
            out.append(v)
    return out


def break_evens(legs: list[ResolvedLeg]) -> list[float]:
    """Exact break-evens: the prices where the P&L at expiry is zero.

    The domain [0, +inf) is split at the strikes. On each segment the P&L is a
    straight line: with a non-zero slope the root is ``a - P(a)/m``, accepted
    only if it falls inside the segment. A segment with zero slope and zero value
    is a whole break-even stretch: its endpoints are reported.
    """
    edges = [0.0, *_sorted_strikes(legs)]
    roots: list[float] = []

    for i, a in enumerate(edges):
        b = edges[i + 1] if i + 1 < len(edges) else math.inf
        pa = pl_at_expiry(legs, a)
        slope = _slope_at_expiry(legs, a)

        if abs(slope) > _TOL:
            root = a - pa / slope
            inside = root >= a - _TOL and (math.isinf(b) or root <= b + _TOL)
            if inside and math.isfinite(root):
                roots.append(max(root, 0.0))
        elif abs(pa) <= _TOL:
            roots.append(a)
            if math.isfinite(b):
                roots.append(b)

    return _dedupe([r for r in roots if r >= 0.0])


def _prob_below(price: float, market: MarketParams, jumps: JumpParams | None = None) -> float:
    """P(S_T < price) under the risk-neutral lognormal distribution (or Merton's)."""
    if jumps is not None and jumps.intensity > 0.0:
        return merton_probability_below(
            price,
            market.spot,
            market.days_to_expiry,
            market.risk_free_rate,
            market.dividend_yield,
            market.iv,
            jumps,
        )
    if price <= 0.0:
        return 0.0
    if math.isinf(price):
        return 1.0
    t = years_from_days(market.days_to_expiry)
    sigma = market.iv
    if t <= 0.0 or sigma <= 0.0:
        return 1.0 if market.spot < price else 0.0
    drift = (market.risk_free_rate - market.dividend_yield - 0.5 * sigma * sigma) * t
    z = (math.log(price / market.spot) - drift) / (sigma * math.sqrt(t))
    return float(norm_cdf(z))


def probability_of_profit(
    legs: list[ResolvedLeg], market: MarketParams, jumps: JumpParams | None = None
) -> float:
    """Probability that the position ends in profit at expiry.

    The final underlying price follows the Black-Scholes lognormal (risk-neutral,
    global IV). The break-evens split the price axis into intervals; on each one
    the sign of the P&L is constant, so checking it at an inner point and adding
    up the probability of the profitable intervals is enough. No simulation: the
    result is exact for the model. With ``jumps`` the price distribution is
    Merton's mixture of lognormals instead.
    """
    edges = [0.0, *break_evens(legs), math.inf]
    total = 0.0
    for a, b in itertools.pairwise(edges):
        if b - a <= _DEDUPE_TOL:
            continue
        probe = a * 2.0 + 1.0 if math.isinf(b) else (a + b) / 2.0
        if pl_at_expiry(legs, probe) > _TOL:
            total += _prob_below(b, market, jumps) - _prob_below(a, market, jumps)
    return min(max(total, 0.0), 1.0)


@dataclass(frozen=True, slots=True)
class PayoffBounds:
    """Payoff extremes. ``math.inf`` means unlimited."""

    max_profit: float
    max_loss: float
    profit_unbounded: bool
    loss_unbounded: bool


def payoff_bounds(legs: list[ResolvedLeg]) -> PayoffBounds:
    """TRUE payoff extremes, not "over the chart range".

    The piecewise payoff reaches its finite extremes only at the corners (S = 0
    and the strikes); the slope of the right-hand ray tells whether profit or
    loss is unlimited. The prototype reported the maximum sampled over the
    visible range, which made the loss of a naked short call look finite.
    """
    strikes = _sorted_strikes(legs)
    vertices = [0.0, *strikes]
    values = [pl_at_expiry(legs, s) for s in vertices]

    right_ray_from = strikes[-1] if strikes else 0.0
    right_slope = _slope_at_expiry(legs, right_ray_from)

    profit_unbounded = right_slope > _TOL
    loss_unbounded = right_slope < -_TOL

    return PayoffBounds(
        max_profit=math.inf if profit_unbounded else max(values),
        max_loss=-math.inf if loss_unbounded else min(values),
        profit_unbounded=profit_unbounded,
        loss_unbounded=loss_unbounded,
    )


# ---------------------------------------------------------------------------
# Trade cost
# ---------------------------------------------------------------------------


def net_cost(legs: list[ResolvedLeg]) -> float:
    """Net cost per unit of underlying.

    Positive = debit (outlay), negative = credit (income).
    """
    return sum(r.signed_qty * r.entry_premium for r in legs)


@dataclass(frozen=True, slots=True)
class LegCost:
    """The cost of a single leg, broken down."""

    resolved: ResolvedLeg
    unit_price: float
    per_contract: float
    units: float
    outflow: float
    inflow: float
    gross: float


@dataclass(frozen=True, slots=True)
class TradeCost:
    """The cost of the whole trade."""

    legs: list[LegCost]
    total_outflow: float
    total_inflow: float
    net: float


def trade_cost(legs: list[ResolvedLeg], sizing: Sizing) -> TradeCost:
    """Turn per-unit prices into the real outlay.

    It is the only place in the engine where the contract multiplier and the
    number of packages enter the calculation.
    """
    detail: list[LegCost] = []
    for r in legs:
        qty = abs(r.signed_qty)
        units = sizing.contract_multiplier * qty * sizing.packages
        gross = r.entry_premium * units
        is_long = r.signed_qty >= 0
        detail.append(
            LegCost(
                resolved=r,
                unit_price=r.entry_premium,
                per_contract=r.entry_premium * sizing.contract_multiplier,
                units=units,
                outflow=gross if is_long else 0.0,
                inflow=0.0 if is_long else gross,
                gross=gross,
            )
        )

    total_outflow = sum(c.outflow for c in detail)
    total_inflow = sum(c.inflow for c in detail)
    return TradeCost(
        legs=detail,
        total_outflow=total_outflow,
        total_inflow=total_inflow,
        net=total_outflow - total_inflow,
    )


# ---------------------------------------------------------------------------
# Moneyness
# ---------------------------------------------------------------------------

MoneynessCode = Literal["ITM", "ATM", "OTM", "STOCK"]

_ATM_BAND = 0.015


def moneyness(leg: Leg, spot: float) -> MoneynessCode:
    """Classify the leg relative to the current price."""
    match leg:
        case StockLeg():
            return "STOCK"
        case OptionLeg(strike=strike, right=right):
            if abs(spot - strike) / strike < _ATM_BAND:
                return "ATM"
            itm = spot > strike if right == "call" else spot < strike
            return "ITM" if itm else "OTM"
