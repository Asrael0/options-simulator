"""Rate, dividend and implied volatility derived from prices (no internet)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from options_simulator.app.carry import (
    Carry,
    RateInfo,
    carry_for,
    exercise_style,
    implied_dividends,
    implied_rate,
    parity_check,
)
from options_simulator.app.market_data import Chain, parse_chain
from options_simulator.pricing import (
    ExerciseStyle,
    OptionSpec,
    implied_volatility,
    price_option,
)

TODAY = date(2026, 10, 3)
SPOT = 100.0
RATE = 0.05
DIVIDEND = 0.02
IV = 0.25


def _synthetic_chain(ticker: str = "_SPX", exercise: ExerciseStyle = "european") -> Chain:
    """Chain priced by the model with a known rate and dividend."""
    options = []
    for days in (60, 180, 365):
        expiry = TODAY + timedelta(days=days)
        for strike in range(80, 125, 5):
            for right, letter in (("call", "C"), ("put", "P")):
                price = price_option(
                    OptionSpec(
                        spot=SPOT,
                        strike=strike,
                        days_to_expiry=days,
                        risk_free_rate=RATE,
                        iv=IV,
                        right=right,  # type: ignore[arg-type]
                        dividend_yield=DIVIDEND,
                    ),
                    exercise,
                    "full",
                )
                options.append(
                    {
                        "option": f"TEST{expiry:%y%m%d}{letter}{strike * 1000:08d}",
                        "bid": round(price - 0.005, 4),
                        "ask": round(price + 0.005, 4),
                        "iv": IV,
                    }
                )
    payload = {
        "symbol": ticker,
        "data": {"symbol": ticker, "current_price": SPOT, "options": options},
    }
    return parse_chain(payload, TODAY)


@pytest.mark.parametrize("exercise", ["european", "american"])
@pytest.mark.parametrize("right", ["call", "put"])
def test_implied_volatility_round_trip(exercise: ExerciseStyle, right: str) -> None:
    spec = OptionSpec(
        spot=100,
        strike=105,
        days_to_expiry=90,
        risk_free_rate=0.04,
        iv=0.37,
        right=right,  # type: ignore[arg-type]
        dividend_yield=0.01,
    )
    price = price_option(spec, exercise, "curve")
    assert implied_volatility(price, spec, exercise) == pytest.approx(0.37, abs=1e-4)


def test_implied_volatility_rejects_impossible_prices() -> None:
    spec = OptionSpec(
        spot=100, strike=90, days_to_expiry=30, risk_free_rate=0.04, iv=0.2, right="call"
    )
    assert implied_volatility(1.0, spec, "european") is None  # below intrinsic value
    assert implied_volatility(0.0, spec, "european") is None


def test_rate_and_dividend_recovered_from_european_chain() -> None:
    chain = _synthetic_chain()
    rate = implied_rate(chain, TODAY)
    assert rate == pytest.approx(RATE, abs=1e-3)
    dividends = implied_dividends(chain, RATE, TODAY)
    assert len(dividends) == 3
    for q in dividends.values():
        assert q == pytest.approx(DIVIDEND, abs=2e-3)


def test_parity_check_improves_with_recovered_values() -> None:
    chain = _synthetic_chain()
    carry = carry_for(chain, RateInfo(RATE, "test", ""), TODAY)
    check = parity_check(chain, carry, TODAY)
    assert check is not None
    assert check.after < 0.05  # calls and puts agree almost perfectly
    assert check.before > check.after


def test_dividend_on_american_chain_is_close() -> None:
    # On American options parity is not exact, but it holds near the money.
    chain = _synthetic_chain("AAPL", "american")
    dividends = implied_dividends(chain, RATE, TODAY)
    assert dividends
    for q in dividends.values():
        assert q == pytest.approx(DIVIDEND, abs=0.01)


def test_exercise_style_and_fallback_dividend() -> None:
    assert exercise_style("_SPX") == "european"
    assert exercise_style("AAPL") == "american"
    carry = Carry(rate=RateInfo(RATE, "test", ""), dividends={}, exercise="american")
    assert carry.dividend(TODAY) == 0.0
    assert carry.dividend_yield is None
