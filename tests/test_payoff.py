"""Tests of the multi-leg P&L against the reference table."""

from __future__ import annotations

import math

import pytest

from options_simulator.pricing import (
    ExerciseStyle,
    Leg,
    ResolvedLeg,
    Sizing,
    break_evens,
    moneyness,
    net_cost,
    payoff_bounds,
    pl_at_expiry,
    pl_at_market,
    resolve_legs,
    trade_cost,
)

from .helpers import market, option, option_at_premium, stock

EUROPEAN: ExerciseStyle = "european"


def build(legs: list[Leg], days: float = 30.0) -> list[ResolvedLeg]:
    return resolve_legs(legs, market(days_to_expiry=days), EUROPEAN)


class TestBearPutSpread:
    """Long put 100 / short put 90."""

    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build([option("put", "long", 100.0), option("put", "short", 90.0)])

    def test_costs_2_862(self, position: list[ResolvedLeg]) -> None:
        assert net_cost(position) == pytest.approx(2.862, abs=5e-4)

    def test_max_profit_is_width_minus_cost(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(7.138, abs=5e-4)
        assert bounds.max_profit == pytest.approx(10.0 - net_cost(position), abs=1e-9)
        assert bounds.profit_unbounded is False

    def test_max_loss_is_the_net_cost(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-2.862, abs=5e-4)
        assert bounds.max_loss == pytest.approx(-net_cost(position), abs=1e-9)
        assert bounds.loss_unbounded is False

    def test_single_break_even_with_exactly_zero_pl(self, position: list[ResolvedLeg]) -> None:
        bes = break_evens(position)
        assert len(bes) == 1
        assert bes[0] == pytest.approx(97.138, abs=5e-4)
        assert abs(pl_at_expiry(position, bes[0])) < 1e-9

    def test_flat_outside_the_strikes(self, position: list[ResolvedLeg]) -> None:
        assert pl_at_expiry(position, 80.0) == pytest.approx(pl_at_expiry(position, 90.0), abs=1e-9)
        assert pl_at_expiry(position, 0.0) == pytest.approx(7.138, abs=5e-4)
        assert pl_at_expiry(position, 110.0) == pytest.approx(
            pl_at_expiry(position, 100.0), abs=1e-9
        )
        assert pl_at_expiry(position, 200.0) == pytest.approx(-2.862, abs=5e-4)


class TestIronCondor:
    """85 / 95 / 105 / 115."""

    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build(
            [
                option("put", "long", 85.0),
                option("put", "short", 95.0),
                option("call", "short", 105.0),
                option("call", "long", 115.0),
            ]
        )

    def test_collects_a_2_693_credit(self, position: list[ResolvedLeg]) -> None:
        assert net_cost(position) == pytest.approx(-2.693, abs=5e-4)

    def test_max_profit_equals_the_credit(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(2.693, abs=5e-4)
        assert bounds.max_profit == pytest.approx(-net_cost(position), abs=1e-9)

    def test_symmetric_loss_on_both_wings(self, position: list[ResolvedLeg]) -> None:
        assert pl_at_expiry(position, 85.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 115.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 85.0) == pytest.approx(
            pl_at_expiry(position, 115.0), abs=1e-9
        )

        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-7.307, abs=5e-4)
        assert bounds.profit_unbounded is False
        assert bounds.loss_unbounded is False

    def test_flat_beyond_the_wings(self, position: list[ResolvedLeg]) -> None:
        assert pl_at_expiry(position, 0.0) == pytest.approx(-7.307, abs=5e-4)
        assert pl_at_expiry(position, 500.0) == pytest.approx(-7.307, abs=5e-4)

    def test_two_break_evens(self, position: list[ResolvedLeg]) -> None:
        bes = break_evens(position)
        assert len(bes) == 2
        assert 85.0 < bes[0] < 95.0
        assert 105.0 < bes[1] < 115.0
        for be in bes:
            assert abs(pl_at_expiry(position, be)) < 1e-9


class TestCollar:
    """Stock @100 + long put 90 + short call 110, T = 60d."""

    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build(
            [
                stock("long", 100.0),
                option("put", "long", 90.0),
                option("call", "short", 110.0),
            ],
            days=60.0,
        )

    def test_constant_floor_below_the_put_strike(self, position: list[ResolvedLeg]) -> None:
        for spot in (0.0, 30.0, 60.0, 89.99, 90.0):
            assert pl_at_expiry(position, spot) == pytest.approx(-9.386, abs=5e-4)
        bounds = payoff_bounds(position)
        assert bounds.max_loss == pytest.approx(-9.386, abs=5e-4)
        assert bounds.loss_unbounded is False

    def test_constant_cap_above_the_call_strike(self, position: list[ResolvedLeg]) -> None:
        for spot in (110.0, 130.0, 400.0):
            assert pl_at_expiry(position, spot) == pytest.approx(10.614, abs=5e-4)
        bounds = payoff_bounds(position)
        assert bounds.max_profit == pytest.approx(10.614, abs=5e-4)
        assert bounds.profit_unbounded is False

    def test_one_to_one_linear_between_strikes(self, position: list[ResolvedLeg]) -> None:
        for spot in range(90, 110):
            delta = pl_at_expiry(position, spot + 1) - pl_at_expiry(position, spot)
            assert delta == pytest.approx(1.0, abs=1e-9)
        assert pl_at_expiry(position, 110.0) - pl_at_expiry(position, 90.0) == pytest.approx(
            20.0, abs=1e-9
        )

    def test_range_equals_strike_distance(self, position: list[ResolvedLeg]) -> None:
        bounds = payoff_bounds(position)
        assert bounds.max_profit - bounds.max_loss == pytest.approx(20.0, abs=1e-9)


class TestUnlimitedExtremes:
    def test_unlimited_profit_of_a_long_call(self) -> None:
        position = build([option("call", "long", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.profit_unbounded is True
        assert bounds.max_profit == math.inf
        assert bounds.loss_unbounded is False
        assert bounds.max_loss == pytest.approx(-net_cost(position), abs=1e-9)

    def test_unlimited_loss_of_a_naked_short_call(self) -> None:
        position = build([option("call", "short", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.loss_unbounded is True
        assert bounds.max_loss == -math.inf
        assert bounds.profit_unbounded is False
        assert bounds.max_profit == pytest.approx(-net_cost(position), abs=1e-9)

    def test_long_put_capped_by_zero_price(self) -> None:
        position = build([option("put", "long", 100.0)])
        bounds = payoff_bounds(position)
        assert bounds.profit_unbounded is False
        assert bounds.max_profit == pytest.approx(100.0 - net_cost(position), abs=1e-9)

    def test_linear_stock_exposure(self) -> None:
        assert payoff_bounds(build([stock("long", 100.0)])).profit_unbounded is True
        assert payoff_bounds(build([stock("short", 100.0)])).loss_unbounded is True


class TestBreakEven:
    def test_single_call_at_strike_plus_premium(self) -> None:
        position = build([option("call", "long", 100.0)])
        bes = break_evens(position)
        assert len(bes) == 1
        assert bes[0] == pytest.approx(100.0 + net_cost(position), abs=1e-9)
        assert abs(pl_at_expiry(position, bes[0])) < 1e-9

    def test_both_break_evens_of_a_straddle(self) -> None:
        position = build([option("call", "long", 100.0), option("put", "long", 100.0)])
        bes = break_evens(position)
        assert len(bes) == 2
        cost = net_cost(position)
        assert bes[0] == pytest.approx(100.0 - cost, abs=1e-9)
        assert bes[1] == pytest.approx(100.0 + cost, abs=1e-9)

    def test_pure_stock_position(self) -> None:
        assert break_evens(build([stock("long", 100.0)])) == [100.0]

    def test_no_break_even_when_always_profitable(self) -> None:
        position = build(
            [
                option_at_premium("call", "short", 100.0, 5.0),
                option_at_premium("call", "long", 100.0, 2.0),
            ]
        )
        assert break_evens(position) == []
        assert pl_at_expiry(position, 100.0) == pytest.approx(3.0, abs=1e-9)

    def test_does_not_duplicate_a_break_even_on_a_strike(self) -> None:
        position = build([option_at_premium("call", "long", 100.0, 0.0)])
        assert break_evens(position) == [0.0, 100.0]


class TestTradeCost:
    @pytest.fixture
    def position(self) -> list[ResolvedLeg]:
        return build([option("call", "long", 100.0), option("call", "short", 110.0)])

    def test_bull_call_spread_5_packages_of_100(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))

        assert cost.total_outflow == pytest.approx(1795.56, abs=5e-3)
        assert cost.total_inflow == pytest.approx(327.60, abs=5e-3)
        assert cost.net == pytest.approx(1467.96, abs=5e-3)

    def test_scales_linearly(self, position: list[ResolvedLeg]) -> None:
        single = trade_cost(position, Sizing(contract_multiplier=100.0, packages=1))
        five = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))
        assert five.net == pytest.approx(single.net * 5.0, abs=1e-9)

        mini = trade_cost(position, Sizing(contract_multiplier=10.0, packages=5))
        assert mini.net == pytest.approx(five.net / 10.0, abs=1e-9)

    def test_negative_net_for_a_credit_position(self) -> None:
        credit = build([option("put", "short", 95.0), option("put", "long", 85.0)])
        cost = trade_cost(credit, Sizing(contract_multiplier=100.0, packages=1))
        assert cost.net < 0.0
        assert cost.total_inflow > cost.total_outflow

    def test_matches_net_cost_per_unit(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=1.0, packages=1))
        assert cost.net == pytest.approx(net_cost(position), abs=1e-9)

    def test_counts_units_leg_by_leg(self, position: list[ResolvedLeg]) -> None:
        cost = trade_cost(position, Sizing(contract_multiplier=100.0, packages=5))
        for leg_cost in cost.legs:
            assert leg_cost.units == 500.0
            assert leg_cost.per_contract == pytest.approx(leg_cost.unit_price * 100.0, abs=1e-9)


class TestLargeQuantities:
    def test_scales_linearly_and_stays_finite(self) -> None:
        one = build([option("call", "long", 100.0)])
        many = build([option("call", "long", 100.0, qty=10_000.0)])

        assert net_cost(many) == pytest.approx(net_cost(one) * 10_000.0, abs=1e-6)
        assert pl_at_expiry(many, 150.0) == pytest.approx(
            pl_at_expiry(one, 150.0) * 10_000.0, abs=1e-6
        )
        assert break_evens(many)[0] == pytest.approx(break_evens(one)[0], abs=1e-9)

        cost = trade_cost(many, Sizing(contract_multiplier=100.0, packages=1000))
        assert math.isfinite(cost.net)


class TestFrozenPremium:
    def test_does_not_change_when_the_market_moves(self) -> None:
        entry = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        premium = entry[0].entry_premium

        before = break_evens(entry)[0]
        assert pl_at_expiry(entry, 120.0) == pytest.approx(20.0 - premium, abs=1e-9)
        assert break_evens(entry)[0] == before

    def test_respects_a_manual_premium(self) -> None:
        position = resolve_legs([option_at_premium("call", "long", 100.0, 5.0)], market(), EUROPEAN)
        assert position[0].entry_premium == 5.0
        assert net_cost(position) == 5.0
        assert break_evens(position)[0] == pytest.approx(105.0, abs=1e-9)

    def test_uses_the_leg_iv_override(self) -> None:
        base = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        skewed = resolve_legs([option("call", "long", 100.0, iv_override=0.5)], market(), EUROPEAN)
        assert skewed[0].entry_premium > base[0].entry_premium

    def test_entry_price_for_the_stock_leg(self) -> None:
        position = resolve_legs([stock("long", 87.5)], market(), EUROPEAN)
        assert position[0].entry_premium == 87.5
        assert pl_at_expiry(position, 100.0) == pytest.approx(12.5, abs=1e-9)


class TestCurrentValue:
    def test_zero_when_the_market_has_not_moved(self) -> None:
        entry_market = market()
        position = resolve_legs([option("call", "long", 100.0)], entry_market, EUROPEAN)
        assert pl_at_market(position, entry_market, EUROPEAN) == pytest.approx(0.0, abs=1e-12)

    def test_isolates_the_vega_effect(self) -> None:
        position = resolve_legs([option("call", "long", 100.0)], market(), EUROPEAN)
        assert pl_at_market(position, market(iv=0.20), EUROPEAN) < 0.0
        assert pl_at_market(position, market(iv=0.40), EUROPEAN) > 0.0

    def test_values_the_stock_leg_at_current_spot(self) -> None:
        position = resolve_legs([stock("long", 100.0)], market(), EUROPEAN)
        assert pl_at_market(position, market(spot=115.0), EUROPEAN) == pytest.approx(15.0, abs=1e-9)


class TestMoneyness:
    def test_classifies_calls_and_puts(self) -> None:
        assert moneyness(option("call", "long", 90.0), 100.0) == "ITM"
        assert moneyness(option("call", "long", 110.0), 100.0) == "OTM"
        assert moneyness(option("put", "long", 110.0), 100.0) == "ITM"
        assert moneyness(option("put", "long", 90.0), 100.0) == "OTM"

    def test_one_and_a_half_percent_atm_band(self) -> None:
        assert moneyness(option("call", "long", 100.0), 100.0) == "ATM"
        assert moneyness(option("call", "long", 100.0), 101.0) == "ATM"
        assert moneyness(option("call", "long", 100.0), 102.0) == "ITM"

    def test_does_not_classify_stock(self) -> None:
        assert moneyness(stock("long", 100.0), 100.0) == "STOCK"


# ---------------------------------------------------------------------------
# Probability of profit
# ---------------------------------------------------------------------------


def test_probability_of_profit_long_call_matches_closed_form() -> None:
    # Long call: profitable above the break-even K + premium. The probability
    # must match N(d2) computed at that price.
    from options_simulator.pricing import norm_cdf, probability_of_profit

    m = market(days_to_expiry=30.0)
    legs = build([option("call", "long", 100.0)])
    (be,) = break_evens(legs)
    t = 30.0 / 365.0
    d2 = (math.log(m.spot / be) + (m.risk_free_rate - m.dividend_yield - 0.5 * m.iv**2) * t) / (
        m.iv * math.sqrt(t)
    )
    assert probability_of_profit(legs, m) == pytest.approx(float(norm_cdf(d2)), abs=1e-12)


def test_probability_of_profit_long_and_short_sum_to_one() -> None:
    from options_simulator.pricing import probability_of_profit

    m = market(days_to_expiry=45.0)
    long_legs = build([option("put", "long", 95.0)], days=45.0)
    short_legs = build([option("put", "short", 95.0)], days=45.0)
    total = probability_of_profit(long_legs, m) + probability_of_profit(short_legs, m)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_probability_of_profit_at_expiry_is_deterministic() -> None:
    from options_simulator.pricing import probability_of_profit

    legs = build([option_at_premium("call", "long", 90.0, 2.0)])
    assert probability_of_profit(legs, market(spot=100.0, days_to_expiry=0.0)) == 1.0
    assert probability_of_profit(legs, market(spot=80.0, days_to_expiry=0.0)) == 0.0
