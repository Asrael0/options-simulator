"""Merton jump calibration on a real option chain.

Picks the quotes worth fitting from one expiry of a CBOE chain and hands them to
``pricing.calibrate_merton``:

  - out-of-the-money options only (puts below the price, calls above): they are
    the most liquid, and on American stock options early exercise is worth
    little there, so the European formula applies;
  - quotes with a real bid and a reasonable spread;
  - strikes within ±30% of the price.

Each quote's implied volatility is recomputed with the same European model and
the same rate and dividend used in the fit, so market and model are measured
with the same ruler.
"""

from __future__ import annotations

from datetime import date

from ..pricing import (
    FitQuote,
    MertonFit,
    OptionSpec,
    Right,
    calibrate_merton,
    implied_volatility,
)
from .market_data import Chain

MONEYNESS = 0.30
MAX_SPREAD = 0.60
MIN_PRICE = 0.05


def fit_quotes(
    chain: Chain, expiry: date, rate: float, dividend: float, today: date | None = None
) -> list[FitQuote]:
    """The quotes of ``expiry`` used for calibration."""
    days = float((expiry - (today or date.today())).days)
    quotes: list[FitQuote] = []
    for strike in chain.strikes(expiry):
        if abs(strike / chain.spot - 1.0) > MONEYNESS:
            continue
        right: Right = "put" if strike < chain.spot else "call"
        quote = chain.quote(expiry, right, strike)
        if quote is None or quote.bid <= 0 or quote.mid is None or quote.mid < MIN_PRICE:
            continue
        if (quote.spread_pct or 9.0) > MAX_SPREAD:
            continue
        spec = OptionSpec(
            spot=chain.spot,
            strike=strike,
            days_to_expiry=days,
            risk_free_rate=rate,
            iv=0.2,
            right=right,
            dividend_yield=dividend,
        )
        iv = implied_volatility(quote.mid, spec, "european", "full")
        if iv is not None:
            quotes.append(FitQuote(strike=strike, right=right, price=quote.mid, iv=iv))
    return quotes


def calibrate_chain(
    chain: Chain, expiry: date, rate: float, dividend: float, today: date | None = None
) -> MertonFit | None:
    """Calibrate Merton on one expiry of ``chain``. ``None`` if there is too little data."""
    day = today or date.today()
    days = float((expiry - day).days)
    if days < 2:
        return None
    return calibrate_merton(
        chain.spot, days, rate, dividend, fit_quotes(chain, expiry, rate, dividend, day)
    )
