"""Tests of Black-Scholes-Merton against the reference table.

Base parameters: S=100, K=100, T=30d, r=4%, IV=30%.

The tests fall into three groups with different purposes:
  - REFERENCE VALUES: exact numbers, taken from the original prototype.
  - STRUCTURAL RELATIONS: properties that must always hold (put-call parity,
    monotonicity in volatility). They do not depend on specific numbers.
  - ROBUSTNESS: edge cases. T = 0, zero volatility, absurd strikes. That is
    where code usually breaks, so that is where tests matter most.
"""

from __future__ import annotations

import math

import pytest

from options_simulator.pricing import (
    black_scholes,
    probability_itm,
    years_from_days,
)

from .helpers import spec


class TestReferenceValues:
    def test_european_atm_call(self) -> None:
        assert black_scholes(spec(right="call")).price == pytest.approx(3.5911, abs=5e-5)

    def test_european_atm_put(self) -> None:
        assert black_scholes(spec(right="put")).price == pytest.approx(3.2629, abs=5e-5)

    def test_atm_call_greeks(self) -> None:
        g = black_scholes(spec(right="call"))
        assert g.delta == pytest.approx(0.5324, abs=5e-5)
        assert g.gamma == pytest.approx(0.0462, abs=5e-5)
        assert g.vega_per_point == pytest.approx(0.1140, abs=5e-5)
        assert g.theta_per_day == pytest.approx(-0.0624, abs=5e-5)


class TestStructuralRelations:
    def test_put_call_parity(self) -> None:
        for strike in (70.0, 90.0, 100.0, 110.0, 140.0):
            for days in (1.0, 30.0, 180.0, 730.0):
                call = black_scholes(spec(strike=strike, days_to_expiry=days, right="call"))
                put = black_scholes(spec(strike=strike, days_to_expiry=days, right="put"))
                t = years_from_days(days)
                expected = 100.0 - strike * math.exp(-0.04 * t)
                assert abs(call.price - put.price - expected) < 1e-9

    def test_parity_with_dividend_yield(self) -> None:
        q = 0.03
        t = years_from_days(90.0)
        call = black_scholes(spec(days_to_expiry=90.0, dividend_yield=q, right="call"))
        put = black_scholes(spec(days_to_expiry=90.0, dividend_yield=q, right="put"))
        expected = 100.0 * math.exp(-q * t) - 100.0 * math.exp(-0.04 * t)
        assert abs(call.price - put.price - expected) < 1e-9

    def test_gamma_and_vega_equal_for_call_and_put(self) -> None:
        for strike in (80.0, 95.0, 100.0, 105.0, 130.0):
            call = black_scholes(spec(strike=strike, right="call"))
            put = black_scholes(spec(strike=strike, right="put"))
            assert call.gamma == put.gamma
            assert call.vega_per_point == put.vega_per_point

    def test_call_delta_minus_put_delta_is_e_minus_qt(self) -> None:
        call = black_scholes(spec(right="call"))
        put = black_scholes(spec(right="put"))
        assert call.delta - put.delta == pytest.approx(1.0, abs=1e-12)

    def test_price_increases_with_volatility(self) -> None:
        previous = -math.inf
        for i in range(1, 31):
            price = black_scholes(spec(iv=i * 0.05)).price
            assert price > previous
            previous = price

    def test_price_above_intrinsic_value(self) -> None:
        for strike in (60.0, 80.0, 100.0, 120.0, 150.0):
            call = black_scholes(spec(strike=strike, right="call")).price
            assert call >= max(100.0 - strike, 0.0) - 1e-12
            assert black_scholes(spec(strike=strike, right="put")).price >= 0.0


class TestRobustness:
    def test_at_expiry_returns_intrinsic_value(self) -> None:
        assert black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="call")).price == 10.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="call")).price == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="put")).price == 10.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="put")).price == 0.0

        itm_call = black_scholes(spec(days_to_expiry=0.0, strike=90.0, right="call"))
        assert itm_call.delta == 1.0
        assert itm_call.gamma == 0.0
        assert itm_call.vega_per_point == 0.0
        assert itm_call.theta_per_day == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="call")).delta == 0.0
        assert black_scholes(spec(days_to_expiry=0.0, strike=110.0, right="put")).delta == -1.0

    def test_negative_expiries_treated_as_expired(self) -> None:
        assert black_scholes(spec(days_to_expiry=-10.0, strike=90.0)).price == 10.0

    def test_iv_towards_zero_converges_to_forward_payoff(self) -> None:
        t = years_from_days(30.0)
        forward = 100.0 * math.exp(0.04 * t)
        expected = math.exp(-0.04 * t) * max(forward - 100.0, 0.0)

        assert black_scholes(spec(iv=0.0)).price == pytest.approx(expected, abs=1e-12)
        for iv in (1e-4, 1e-5, 1e-6):
            assert black_scholes(spec(iv=iv)).price == pytest.approx(expected, abs=1e-6)

    def test_strikes_far_from_spot(self) -> None:
        far_otm_call = black_scholes(spec(strike=100_000.0, right="call"))
        assert math.isfinite(far_otm_call.price)
        assert 0.0 <= far_otm_call.price < 1e-9
        assert far_otm_call.delta == pytest.approx(0.0, abs=1e-9)

        deep_itm_call = black_scholes(spec(strike=0.01, right="call"))
        assert math.isfinite(deep_itm_call.price)
        assert deep_itm_call.delta == pytest.approx(1.0, abs=1e-6)

        far_otm_put = black_scholes(spec(strike=0.01, right="put"))
        assert 0.0 <= far_otm_put.price < 1e-9

        for g in (far_otm_call, deep_itm_call, far_otm_put):
            assert math.isfinite(g.gamma)
            assert math.isfinite(g.vega_per_point)
            assert math.isfinite(g.theta_per_day)
            assert math.isfinite(g.rho_per_point)

    def test_zero_spot_or_strike(self) -> None:
        zero_spot = black_scholes(spec(spot=0.0, right="put"))
        assert math.isfinite(zero_spot.price)
        expected = 100.0 * math.exp(-0.04 * years_from_days(30.0))
        assert zero_spot.price == pytest.approx(expected, abs=1e-12)
        assert math.isfinite(black_scholes(spec(strike=0.0)).price)

    def test_long_expiries_and_extreme_iv(self) -> None:
        long_dated = black_scholes(spec(days_to_expiry=3650.0, iv=2.5))
        assert math.isfinite(long_dated.price)
        assert 0.0 < long_dated.price < 100.0


class TestProbabilityItm:
    def test_just_below_half_for_an_atm_call(self) -> None:
        p = probability_itm(spec(right="call"))
        assert 0.4 < p < 0.5

    def test_call_and_put_are_complementary(self) -> None:
        for strike in (85.0, 100.0, 120.0):
            call = probability_itm(spec(strike=strike, right="call"))
            put = probability_itm(spec(strike=strike, right="put"))
            assert call + put == pytest.approx(1.0, abs=1e-12)

    def test_decreases_as_strike_increases(self) -> None:
        previous = math.inf
        for strike in (80.0, 90.0, 100.0, 110.0, 120.0):
            p = probability_itm(spec(strike=strike, right="call"))
            assert p < previous
            previous = p

    def test_degenerates_at_expiry(self) -> None:
        assert probability_itm(spec(days_to_expiry=0.0, strike=90.0, right="call")) == 1.0
        assert probability_itm(spec(days_to_expiry=0.0, strike=110.0, right="call")) == 0.0
