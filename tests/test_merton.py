"""Tests of the Merton jump-diffusion model and its calibration."""

from __future__ import annotations

import math

import numpy as np
import pytest

from options_simulator.pricing import (
    NO_JUMPS,
    FitQuote,
    JumpParams,
    Right,
    black_scholes,
    calibrate_merton,
    implied_volatility,
    merton_price,
    merton_prices,
    years_from_days,
)

from .helpers import spec

CRASHES = JumpParams(intensity=1.0, mean=-0.10, vol=0.15)


class TestPricing:
    @pytest.mark.parametrize("right", ["call", "put"])
    @pytest.mark.parametrize("strike", [80.0, 100.0, 120.0])
    def test_without_jumps_it_is_black_scholes(self, right: str, strike: float) -> None:
        s = spec(strike=strike, right=right, dividend_yield=0.02)
        assert merton_price(s, NO_JUMPS) == black_scholes(s).price
        vectorised = merton_prices(
            100.0, np.array([strike]), np.array([right == "call"]), 30.0, 0.04, 0.02, 0.30, NO_JUMPS
        )
        assert vectorised[0] == pytest.approx(black_scholes(s).price, abs=1e-12)

    @pytest.mark.parametrize("strike", [70.0, 95.0, 100.0, 130.0])
    def test_put_call_parity_holds(self, strike: float) -> None:
        call = merton_price(spec(strike=strike, right="call", days_to_expiry=90.0), CRASHES)
        put = merton_price(spec(strike=strike, right="put", days_to_expiry=90.0), CRASHES)
        t = years_from_days(90.0)
        assert call - put == pytest.approx(100.0 - strike * math.exp(-0.04 * t), abs=1e-10)

    def test_matches_monte_carlo(self) -> None:
        rng = np.random.default_rng(7)
        paths = 1_000_000
        t, r, sigma = 0.5, 0.04, 0.2
        lam, mean, vol = CRASHES.intensity, CRASHES.mean, CRASHES.vol
        k = CRASHES.expected_jump
        jumps = rng.poisson(lam * t, paths)
        log_jumps = jumps * mean + np.sqrt(jumps) * vol * rng.standard_normal(paths)
        drift = (r - lam * k - 0.5 * sigma * sigma) * t
        final = 100.0 * np.exp(
            drift + sigma * math.sqrt(t) * rng.standard_normal(paths) + log_jumps
        )
        put_mc = math.exp(-r * t) * float(np.mean(np.maximum(90.0 - final, 0.0)))

        put = merton_price(
            spec(strike=90.0, right="put", days_to_expiry=t * 365.0, iv=sigma), CRASHES
        )
        assert put == pytest.approx(put_mc, abs=0.03)

    def test_crash_risk_creates_a_skew(self) -> None:
        def iv(strike: float, right: str) -> float:
            s = spec(strike=strike, right=right, days_to_expiry=60.0, iv=0.2)
            value = implied_volatility(merton_price(s, CRASHES), s, "european", "full")
            assert value is not None
            return value

        low_put, atm, high_call = iv(80.0, "put"), iv(100.0, "call"), iv(120.0, "call")
        assert low_put > atm
        assert low_put > high_call

    def test_jumps_make_options_dearer(self) -> None:
        s = spec(strike=85.0, right="put", days_to_expiry=60.0)
        assert merton_price(s, CRASHES) > black_scholes(s).price

    def test_at_expiry_returns_intrinsic_value(self) -> None:
        assert merton_price(spec(strike=90.0, days_to_expiry=0.0), CRASHES) == 10.0
        assert merton_price(spec(strike=90.0, right="put", days_to_expiry=0.0), CRASHES) == 0.0


def _quotes(sigma: float, jumps: JumpParams, days: float) -> list[FitQuote]:
    """A synthetic chain priced by Merton itself: out-of-the-money options only."""
    quotes = []
    for strike in np.arange(70.0, 131.0, 2.5):
        right: Right = "put" if strike < 100.0 else "call"
        s = spec(strike=float(strike), right=right, days_to_expiry=days, iv=sigma)
        price = merton_price(s, jumps)
        iv = implied_volatility(price, s, "european", "full")
        if iv is not None and price > 0.01:
            quotes.append(FitQuote(strike=float(strike), right=right, price=price, iv=iv))
    return quotes


class TestCalibration:
    def test_fits_a_chain_with_jumps_much_better_than_one_volatility(self) -> None:
        quotes = _quotes(0.18, CRASHES, 60.0)
        fit = calibrate_merton(100.0, 60.0, 0.04, 0.0, quotes)
        assert fit is not None
        assert fit.rmse < 0.15  # IV points
        assert fit.bsm_rmse > 5 * fit.rmse
        assert fit.jumps.expected_jump < 0  # it finds crashes, not rallies

    def test_a_flat_chain_needs_no_meaningful_jumps(self) -> None:
        quotes = _quotes(0.25, NO_JUMPS, 45.0)
        fit = calibrate_merton(100.0, 45.0, 0.04, 0.0, quotes)
        assert fit is not None
        assert fit.rmse < 0.1
        assert fit.bsm_rmse < 0.01

    def test_too_few_quotes(self) -> None:
        assert calibrate_merton(100.0, 30.0, 0.04, 0.0, _quotes(0.2, CRASHES, 30.0)[:3]) is None
