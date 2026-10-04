"""Tests of the CRR binomial tree.

These tests check PROPERTIES rather than fixed values: that the tree converges
to the closed formula, that an American option is always worth at least the
European one, that gamma is smooth. Testing properties instead of numbers is
more robust: it survives a change of implementation.
"""

from __future__ import annotations

import itertools
import math

import pytest

from options_simulator.pricing import (
    binomial_price,
    binomial_price_and_greeks,
    black_scholes,
)

from .helpers import spec


class TestConvergence:
    def test_converges_to_the_analytical_price(self) -> None:
        analytic = black_scholes(spec()).price

        def error_at(steps: int) -> float:
            return abs(binomial_price(spec(), "european", steps) - analytic)

        assert error_at(5000) < error_at(500)
        assert error_at(500) < error_at(50)
        assert error_at(5000) < 1e-3

    def test_500_steps_give_3_5894(self) -> None:
        assert binomial_price(spec(), "european", 500) == pytest.approx(3.5894, abs=5e-5)
        assert black_scholes(spec()).price == pytest.approx(3.5911, abs=5e-5)

    def test_converges_on_the_put_too(self) -> None:
        analytic = black_scholes(spec(right="put")).price
        assert binomial_price(spec(right="put"), "european", 5000) == pytest.approx(
            analytic, abs=1e-3
        )


class TestAmericanExercise:
    def test_american_call_without_dividends_equals_european(self) -> None:
        for steps in (50, 140, 500):
            for strike in (80.0, 100.0, 120.0):
                s = spec(strike=strike, right="call")
                assert binomial_price(s, "american", steps) == binomial_price(s, "european", steps)

    def test_american_put_always_worth_at_least_the_european(self) -> None:
        for strike in (70.0, 90.0, 100.0, 110.0, 130.0):
            for days in (30.0, 90.0, 365.0):
                for rate in (0.0, 0.04, 0.10):
                    s = spec(
                        strike=strike,
                        days_to_expiry=days,
                        risk_free_rate=rate,
                        right="put",
                    )
                    american = binomial_price(s, "american", 140)
                    european = binomial_price(s, "european", 140)
                    assert american >= european - 1e-12

    def test_early_exercise_premium_on_itm_put(self) -> None:
        s = spec(spot=80.0, strike=100.0, days_to_expiry=90.0, risk_free_rate=0.06, right="put")
        american = binomial_price(s, "american", 500)
        assert american == pytest.approx(20.00, abs=5e-3)
        assert black_scholes(s).price == pytest.approx(19.02, abs=5e-3)
        assert american > black_scholes(s).price

    def test_american_put_never_below_immediate_exercise(self) -> None:
        for spot in (40.0, 60.0, 80.0, 95.0):
            s = spec(
                spot=spot,
                strike=100.0,
                days_to_expiry=90.0,
                risk_free_rate=0.06,
                right="put",
            )
            assert binomial_price(s, "american", 200) >= 100.0 - spot - 1e-9


class TestGreeksReadFromTheTree:
    """Delta, gamma and theta are read at levels 1 and 2 of the tree.

    So they hold at t = dt and t = 2*dt rather than t = 0. With 140 steps over 30
    days the shift is about 0.4 days and causes a bias below 1% on gamma and
    theta. In exchange the curves are SMOOTH: finite differences divide by h²,
    amplifying the CRR sawtooth into a ~2% jitter.
    """

    def test_matches_the_analytical_greeks(self) -> None:
        analytic = black_scholes(spec())
        tree = binomial_price_and_greeks(spec(), "american", 140)

        assert tree.delta == pytest.approx(analytic.delta, abs=1e-3)
        assert abs(tree.gamma / analytic.gamma - 1.0) < 0.01
        assert abs(tree.theta_per_day / analytic.theta_per_day - 1.0) < 0.01
        assert abs(tree.vega_per_point / analytic.vega_per_point - 1.0) < 0.01
        assert abs(tree.rho_per_point / analytic.rho_per_point - 1.0) < 0.01

    def test_gamma_is_smooth_across_spot(self) -> None:
        gammas = [
            binomial_price_and_greeks(spec(spot=98.0 + i * 0.25), "american", 140).gamma
            for i in range(17)
        ]
        for previous, current in itertools.pairwise(gammas):
            assert abs(current / previous - 1.0) < 0.02

    def test_greek_signs(self) -> None:
        assert binomial_price_and_greeks(spec(right="call"), "american", 140).delta > 0
        assert binomial_price_and_greeks(spec(right="put"), "american", 140).delta < 0

        for right in ("call", "put"):
            g = binomial_price_and_greeks(spec(right=right), "american", 140)
            assert g.gamma > 0
            assert g.vega_per_point > 0
            assert g.theta_per_day < 0


class TestRobustness:
    def test_at_expiry_returns_intrinsic_value(self) -> None:
        assert binomial_price(spec(days_to_expiry=0.0, strike=90.0), "american", 140) == 10.0
        assert binomial_price(spec(days_to_expiry=0.0, strike=110.0), "american", 140) == 0.0

    def test_iv_towards_zero_keeps_probabilities_in_range(self) -> None:
        for iv in (0.0, 1e-8, 1e-5, 1e-4, 1e-3):
            for days in (30.0, 365.0, 1825.0):
                for right in ("call", "put"):
                    price = binomial_price(
                        spec(iv=iv, days_to_expiry=days, right=right), "american", 140
                    )
                    assert math.isfinite(price)
                    assert 0.0 <= price <= 100.0 + 1e-9

    def test_stays_finite_with_extreme_iv(self) -> None:
        price = binomial_price(spec(iv=5.0), "american", 140)
        assert math.isfinite(price)
        assert 0.0 < price <= 100.0

    def test_strikes_far_from_spot(self) -> None:
        assert binomial_price(spec(strike=100_000.0), "american", 140) == pytest.approx(
            0.0, abs=1e-9
        )
        deep_itm = binomial_price(spec(strike=0.01, right="call"), "american", 140)
        assert 99.0 < deep_itm < 101.0

    def test_minimum_of_two_steps(self) -> None:
        for steps in (0, 1, 2):
            g = binomial_price_and_greeks(spec(), "american", steps)
            assert math.isfinite(g.price)
            assert math.isfinite(g.gamma)

    def test_dividend_yield_in_the_drift(self) -> None:
        no_div = binomial_price(spec(right="call"), "european", 500)
        with_div = binomial_price(spec(right="call", dividend_yield=0.05), "european", 500)
        assert with_div < no_div
        assert with_div == pytest.approx(
            black_scholes(spec(right="call", dividend_yield=0.05)).price, abs=5e-3
        )

    def test_early_exercise_of_a_call_with_dividends(self) -> None:
        s = spec(
            spot=130.0,
            strike=100.0,
            days_to_expiry=365.0,
            dividend_yield=0.12,
            right="call",
        )
        assert binomial_price(s, "american", 500) > binomial_price(s, "european", 500)
