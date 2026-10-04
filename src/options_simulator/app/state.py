"""Position state and derived values.

The bridge between the interface and the engine. It holds two things:

  ``PositionState`` — everything the user can change: ticker, market
  parameters, legs, sizing. Only data and the methods that change it.

  ``compute()``     — takes that state and produces ``Analytics``: every derived
  number (cost, Greeks, break-evens, payoff curve…) in one go, by calling the
  engine.

The state is DELIBERATELY DUMB: no financial maths in its methods. If pricing
lived inside the setters, every slider move would rebuild the binomial tree in
the middle of a UI event handler, and it would no longer be clear how often.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ..pricing import (
    ExerciseStyle,
    Greeks,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    Resolution,
    ResolvedLeg,
    Right,
    Side,
    Sizing,
    StockLeg,
    TheoreticalPremium,
    TradeCost,
    break_evens,
    net_cost,
    payoff_bounds,
    pl_at_expiry,
    pl_at_market,
    position_greeks,
    price_option,
    probability_of_profit,
    resolve_legs,
    spec_for_leg,
    trade_cost,
)
from .strategies import STRATEGIES, new_leg_id

INITIAL_MARKET = MarketParams(
    spot=100.0,
    days_to_expiry=30.0,
    risk_free_rate=0.04,
    iv=0.30,
    dividend_yield=0.0,
)

LegType = Right | str


@dataclass(slots=True)
class PositionState:
    """Everything the user can change."""

    ticker: str = "AAPL"
    name: str = "Apple Inc."
    market: MarketParams = INITIAL_MARKET
    entry_market: MarketParams = INITIAL_MARKET
    pin_premiums: bool = True
    exercise: ExerciseStyle = "european"
    compare_exercise: bool = False
    legs: list[Leg] = field(default_factory=lambda: STRATEGIES["single"].build(100.0))
    strategy_key: str = "single"
    target: float = 100.0
    iv_sim: float = 0.30
    sizing: Sizing = field(default_factory=Sizing)
    currency: str = "$"

    # Chart-only settings, not saved with the position.
    days_forward: float = 0.0
    comparison: PositionState | None = None
    comparison_name: str = ""

    # -- market ------------------------------------------------------------

    def set_market(self, **changes: float) -> None:
        # The scenario follows the price until the user moves it elsewhere.
        if "spot" in changes and abs(self.target - self.market.spot) < 1e-9:
            self.target = changes["spot"]
        self.market = replace(self.market, **changes)
        if "iv" in changes:
            self.iv_sim = changes["iv"]
        if not self.pin_premiums:
            self.entry_market = self.market

    def set_pin_premiums(self, pinned: bool) -> None:
        self.pin_premiums = pinned
        if pinned:
            self.entry_market = self.market

    def reprice_entry(self) -> None:
        """Re-anchor the theoretical premiums to the current market parameters."""
        self.entry_market = self.market

    # -- legs --------------------------------------------------------------

    def apply_strategy(self, key: str) -> None:
        strategy = STRATEGIES.get(key)
        if strategy is None:
            return
        self.strategy_key = key
        self.legs = strategy.build(self.market.spot)
        self.entry_market = self.market

    def add_leg(self) -> None:
        self.legs.append(
            OptionLeg(
                leg_id=new_leg_id(),
                side="long",
                qty=1.0,
                right="call",
                strike=round(self.market.spot),
            )
        )

    def remove_leg(self, leg_id: str) -> None:
        if len(self.legs) > 1:
            self.legs = [leg for leg in self.legs if leg.leg_id != leg_id]

    def _replace_leg(self, leg_id: str, new_leg: Leg) -> None:
        self.legs = [new_leg if leg.leg_id == leg_id else leg for leg in self.legs]

    def _find(self, leg_id: str) -> Leg | None:
        return next((leg for leg in self.legs if leg.leg_id == leg_id), None)

    def set_leg_type(self, leg_id: str, leg_type: str) -> None:
        leg = self._find(leg_id)
        if leg is None:
            return
        if leg_type == "stock":
            if isinstance(leg, StockLeg):
                return
            self._replace_leg(
                leg_id,
                StockLeg(leg_id=leg.leg_id, side=leg.side, qty=leg.qty, entry_price=leg.strike),
            )
            return
        right: Right = "call" if leg_type == "call" else "put"
        if isinstance(leg, StockLeg):
            self._replace_leg(
                leg_id,
                OptionLeg(
                    leg_id=leg.leg_id,
                    side=leg.side,
                    qty=leg.qty,
                    right=right,
                    strike=leg.entry_price,
                ),
            )
            return
        self._replace_leg(leg_id, replace(leg, right=right, premium=TheoreticalPremium()))

    def set_leg_side(self, leg_id: str, side: Side) -> None:
        leg = self._find(leg_id)
        if leg is not None:
            self._replace_leg(leg_id, replace(leg, side=side))

    def set_leg_strike(self, leg_id: str, value: float) -> None:
        leg = self._find(leg_id)
        if leg is None or value is None:
            return
        if isinstance(leg, StockLeg):
            self._replace_leg(leg_id, replace(leg, entry_price=float(value)))
        else:
            self._replace_leg(leg_id, replace(leg, strike=float(value)))

    def set_leg_qty(self, leg_id: str, value: float) -> None:
        leg = self._find(leg_id)
        if leg is None or value is None:
            return
        self._replace_leg(leg_id, replace(leg, qty=max(1.0, round(float(value)))))

    def set_leg_premium(self, leg_id: str, value: float | None) -> None:
        leg = self._find(leg_id)
        if not isinstance(leg, OptionLeg):
            return
        premium = TheoreticalPremium() if value is None else ManualPremium(float(value))
        self._replace_leg(leg_id, replace(leg, premium=premium))

    def reset_premiums(self) -> None:
        self.legs = [
            replace(leg, premium=TheoreticalPremium()) if isinstance(leg, OptionLeg) else leg
            for leg in self.legs
        ]

    def has_manual_premiums(self) -> bool:
        return any(
            isinstance(leg, OptionLeg) and isinstance(leg.premium, ManualPremium)
            for leg in self.legs
        )


@dataclass(frozen=True, slots=True)
class PayoffPoint:
    spot: float
    expiry: float
    today: float
    today_other: float | None
    scenario: float | None
    compare: float | None


@dataclass(frozen=True, slots=True)
class Analytics:
    """Every derived value, computed in one batch."""

    net_cost: float
    greeks: Greeks
    break_evens: list[float]
    max_profit: float
    max_loss: float
    profit_unbounded: bool
    loss_unbounded: bool
    cost: TradeCost
    payoff: list[PayoffPoint]
    chart_low: float
    chart_high: float
    entry_premiums: dict[str, float]
    other_exercise: ExerciseStyle | None
    scenario: Scenario
    scenario_curve: bool
    prob_profit: float
    comparison_name: str | None


# ---------------------------------------------------------------------------
# Scenario: price, date and volatility chosen by the user
# ---------------------------------------------------------------------------

# Scenario matrix: price and IV changes relative to today.
MATRIX_PRICE_MOVES = (-0.10, -0.05, -0.025, 0.0, 0.025, 0.05, 0.10)
MATRIX_IV_MOVES = (-0.50, -0.25, 0.0, 0.25, 0.50)


@dataclass(frozen=True, slots=True)
class ScenarioLeg:
    leg_id: str
    entry: float
    value: float
    pl: float


@dataclass(frozen=True, slots=True)
class Scenario:
    """The P&L in a scenario, and where it comes from.

    ``pl_today`` is the P&L if the position were closed now. The effects are
    computed in sequence — first the price moves, then time passes, then
    volatility changes — so they add up exactly:
    ``pl = pl_today + effect_price + effect_time + effect_vol``.
    """

    price: float
    days: float
    iv: float
    pl_today: float
    pl: float
    effect_price: float
    effect_time: float
    effect_vol: float
    legs: list[ScenarioLeg]
    matrix: list[list[float]]  # matrix[IV row][price column]


def scenario_market_of(state: PositionState) -> MarketParams:
    """Scenario market: chosen price, days moved forward, chosen IV."""
    dte = state.market.days_to_expiry
    return replace(
        state.market,
        spot=state.target,
        days_to_expiry=max(dte - min(state.days_forward, dte), 0.0),
        iv=state.iv_sim,
    )


def compute_scenario(state: PositionState, resolved: list[ResolvedLeg]) -> Scenario:
    now = state.market
    target = scenario_market_of(state)

    def pl(market: MarketParams) -> float:
        return pl_at_market(resolved, market, state.exercise)

    pl_today = pl(now)
    moved = replace(now, spot=target.spot)
    aged = replace(moved, days_to_expiry=target.days_to_expiry)
    pl_moved, pl_aged, pl_final = pl(moved), pl(aged), pl(target)

    legs: list[ScenarioLeg] = []
    for r in resolved:
        value = (
            target.spot
            if isinstance(r.leg, StockLeg)
            else price_option(spec_for_leg(r.leg, target), state.exercise)
        )
        legs.append(
            ScenarioLeg(
                leg_id=r.leg.leg_id,
                entry=r.entry_premium,
                value=value,
                pl=r.signed_qty * (value - r.entry_premium),
            )
        )

    matrix = [
        [
            pl_at_market(
                resolved,
                replace(
                    target,
                    spot=now.spot * (1 + dp),
                    iv=max(now.iv * (1 + dv), 0.01),
                ),
                state.exercise,
                "curve",
            )
            for dp in MATRIX_PRICE_MOVES
        ]
        for dv in MATRIX_IV_MOVES
    ]

    return Scenario(
        price=target.spot,
        days=now.days_to_expiry - target.days_to_expiry,
        iv=target.iv,
        pl_today=pl_today,
        pl=pl_final,
        effect_price=pl_moved - pl_today,
        effect_time=pl_aged - pl_moved,
        effect_vol=pl_final - pl_aged,
        legs=legs,
        matrix=matrix,
    )


def compute(state: PositionState) -> Analytics:
    """Recompute everything that depends on the state.

    A single function instead of many scattered properties: it makes the cost
    of an update obvious, and shows at once if something is recomputed more
    often than needed.
    """
    premium_market = state.entry_market if state.pin_premiums else state.market
    resolved = resolve_legs(state.legs, premium_market, state.exercise)

    bounds = payoff_bounds(resolved)
    bes = break_evens(resolved)

    references = [
        leg.entry_price if isinstance(leg, StockLeg) else leg.strike for leg in state.legs
    ]
    # Chart width: about three standard deviations of the price at expiry,
    # between 10% and 45% of spot. A 9-day expiry is not squeezed into a strip,
    # and a one-year expiry gets room.
    spot = state.market.spot
    spread = state.market.iv * math.sqrt(max(state.market.days_to_expiry, 1.0) / 365.0)
    width = min(max(3.0 * spread, 0.10), 0.45)
    low = max(min(spot * (1 - width), min(references) * 0.97), 0.0)
    high = max(spot * (1 + width), max(references) * 1.03)

    # Comparison curve with the opposite exercise style. It uses the SAME
    # premiums paid, so the gap between the two curves is only the value of
    # early exercise, not a difference in cost.
    other_exercise: ExerciseStyle | None = None
    if state.compare_exercise and any(isinstance(leg, OptionLeg) for leg in state.legs):
        other_exercise = "european" if state.exercise == "american" else "american"

    uses_tree = state.exercise == "american" or other_exercise is not None
    steps = 70 if uses_tree else 140
    xs = {low + (high - low) * i / steps for i in range(steps + 1)}
    xs.update(x for x in (*references, *bes, state.market.spot, state.target) if low < x < high)

    # Scenario curve: N days ahead with the scenario IV. Drawn only when it
    # differs from «today» in at least one of the two.
    scenario_market = scenario_market_of(state)
    scenario_curve = (
        scenario_market.days_to_expiry != state.market.days_to_expiry
        or abs(scenario_market.iv - state.market.iv) > 1e-12
    )

    # Comparison with another position: only the at-expiry P&L, per unit.
    compared: list[ResolvedLeg] | None = None
    if state.comparison is not None:
        other = state.comparison
        compared = resolve_legs(
            other.legs,
            other.entry_market if other.pin_premiums else other.market,
            other.exercise,
        )

    resolution: Resolution = "curve"

    payoff: list[PayoffPoint] = []
    for spot in sorted(xs):
        at_spot = replace(state.market, spot=spot)
        today = pl_at_market(resolved, at_spot, state.exercise, resolution)
        payoff.append(
            PayoffPoint(
                spot=spot,
                expiry=pl_at_expiry(resolved, spot),
                today=today,
                today_other=(
                    pl_at_market(resolved, at_spot, other_exercise, resolution)
                    if other_exercise is not None
                    else None
                ),
                scenario=(
                    pl_at_market(
                        resolved, replace(scenario_market, spot=spot), state.exercise, resolution
                    )
                    if scenario_curve
                    else None
                ),
                compare=pl_at_expiry(compared, spot) if compared is not None else None,
            )
        )

    return Analytics(
        net_cost=net_cost(resolved),
        greeks=position_greeks(resolved, state.market, state.exercise),
        break_evens=bes,
        max_profit=bounds.max_profit,
        max_loss=bounds.max_loss,
        profit_unbounded=bounds.profit_unbounded,
        loss_unbounded=bounds.loss_unbounded,
        cost=trade_cost(resolved, state.sizing),
        payoff=payoff,
        chart_low=low,
        chart_high=high,
        entry_premiums={r.leg.leg_id: r.entry_premium for r in resolved},
        other_exercise=other_exercise,
        scenario=compute_scenario(state, resolved),
        scenario_curve=scenario_curve,
        prob_profit=probability_of_profit(resolved, state.market),
        comparison_name=state.comparison_name if compared is not None else None,
    )


# ---------------------------------------------------------------------------
# Price x time heat map
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Heatmap:
    """P&L on a grid: rows = days from today, columns = prices."""

    prices: list[float]
    days: list[float]
    values: list[list[float]]  # values[row][column]


HEATMAP_PRICES = 25
HEATMAP_ROWS = 11


def compute_heatmap(state: PositionState, analytics: Analytics) -> Heatmap:
    """Position P&L as price and elapsed days change.

    Kept apart from ``compute`` because it costs much more (hundreds of prices,
    binomial trees for American options): the page calls it only while the map
    tab is open.
    """
    premium_market = state.entry_market if state.pin_premiums else state.market
    resolved = resolve_legs(state.legs, premium_market, state.exercise)
    low, high = analytics.chart_low, analytics.chart_high
    prices = [low + (high - low) * i / (HEATMAP_PRICES - 1) for i in range(HEATMAP_PRICES)]
    dte = state.market.days_to_expiry
    days = [dte * j / (HEATMAP_ROWS - 1) for j in range(HEATMAP_ROWS)]
    values = [
        [
            pl_at_expiry(resolved, price)
            if elapsed >= dte
            else pl_at_market(
                resolved,
                replace(state.market, spot=price, days_to_expiry=dte - elapsed),
                state.exercise,
                "curve",
            )
            for price in prices
        ]
        for elapsed in days
    ]
    return Heatmap(prices=prices, days=days, values=values)
