"""Interest rate and dividend derived from option prices.

The model needs two numbers the market does not publish anywhere: the risk-free
rate and the stock's dividend. Guessing them (4% and 0%) misprices options,
especially on stocks with high dividends. Here they are derived from the options
themselves, through PUT-CALL PARITY.

THE IDEA. A bought call and a sold put on the same strike K behave, at expiry,
exactly like owning the stock and having to pay K. So today:

    C − P = S·e^(−qT) − K·e^(−rT)        (European options)

  - RATE: as K changes, C − P falls by e^(−rT) for every dollar of strike. The
    slope of the line gives r. This is done on S&P 500 options (index ``_SPX``),
    which are European: there the formula holds exactly.
  - DIVIDEND: with r known, C − P at the strikes near the price gives the
    forward F = K + (C − P)·e^(rT), and from it q = r − ln(F/S)/T, expiry by
    expiry. On American stock options only near-the-money strikes are used,
    where early exercise matters little.

The "dividend" obtained this way is really everything that separates the forward
from spot: dividends, the borrow cost for short sellers, small price
mismatches. That is why the interface calls it «implied yield».

THE CHECK. With the right rate and dividend, a call and a put on the same strike
must have the same implied volatility. ``parity_check`` measures how far apart
they are before and after: the honest way to know whether the derived numbers
really improve the model.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ..pricing import ExerciseStyle, OptionSpec, implied_volatility
from . import auth
from .market_data import Chain, MarketDataError, fetch_chain
from .tickers import is_index

DEFAULT_RATE = 0.04
RATE_SYMBOL = "_SPX"
RATE_CACHE_SECONDS = 6 * 3600
RATE_MIN, RATE_MAX = 0.0, 0.15
DIVIDEND_LIMIT = 0.5  # beyond ±50% a year the data is certainly broken

NEAR_STRIKES = 4
MAX_SPREAD = 0.30

# Shown through tr() in the interface.
RATE_FROM_SPX = "ricavato dalle opzioni sull'S&P 500"
RATE_DEFAULT = "valore predefinito (S&P 500 non disponibile)"


@dataclass(frozen=True, slots=True)
class RateInfo:
    rate: float
    source: str  # text to display: where the rate comes from
    measured_at: str


@dataclass(frozen=True, slots=True)
class Carry:
    """Market rate and the stock's implied yield, per expiry."""

    rate: RateInfo
    dividends: dict[date, float]
    exercise: ExerciseStyle

    def dividend(self, expiry: date) -> float:
        return self.dividends.get(expiry, self.dividend_yield or 0.0)

    @property
    def dividend_yield(self) -> float | None:
        """Summary value: median over the expiries between 1 month and 1.5 years.

        Very short expiries are too noisy (a few days amplify every cent of
        error) and are affected by a single dividend payment.
        """
        today = date.today()
        middle = [q for e, q in self.dividends.items() if 30 <= (e - today).days <= 580]
        values = middle or list(self.dividends.values())
        return statistics.median(values) if values else None


@dataclass(frozen=True, slots=True)
class ParityCheck:
    """Median gap between call and put IV on the same strike, in % points."""

    before: float  # with the default rate and zero dividend
    after: float  # with the derived rate and dividend
    pairs: int


def exercise_style(ticker: str) -> ExerciseStyle:
    """Index options (symbols with «_») are European, all others American."""
    return "european" if is_index(ticker) else "american"


def _years(expiry: date, today: date) -> float:
    return (expiry - today).days / 365.0


def _pairs(chain: Chain, expiry: date, *, max_distance: float) -> list[tuple[float, float]]:
    """(strike, C − P) for the strikes where both call and put are quoted and liquid."""
    out: list[tuple[float, float]] = []
    for strike in chain.strikes(expiry):
        if abs(strike / chain.spot - 1) > max_distance + 1e-9:
            continue
        call = chain.quote(expiry, "call", strike)
        put = chain.quote(expiry, "put", strike)
        if call is None or put is None or call.bid <= 0 or put.bid <= 0:
            continue
        if (call.spread_pct or 9) > MAX_SPREAD or (put.spread_pct or 9) > MAX_SPREAD:
            continue
        if call.mid is None or put.mid is None:
            continue
        out.append((strike, call.mid - put.mid))
    return out


# ---------------------------------------------------------------------------
# Rate
# ---------------------------------------------------------------------------


def implied_rate(chain: Chain, today: date) -> float | None:
    """Rate from the slope of C − P against strike (European options only).

    One line per expiry; the median is taken over the expiries between 2 months
    and 2.5 years, where the estimate is stable.
    """
    estimates: list[float] = []
    for expiry in chain.expiries:
        t = _years(expiry, today)
        if not 0.15 <= t <= 2.5:
            continue
        points = _pairs(chain, expiry, max_distance=0.10)
        if len(points) < 5:
            continue
        n = len(points)
        mean_k = sum(k for k, _ in points) / n
        mean_y = sum(y for _, y in points) / n
        sxx = sum((k - mean_k) ** 2 for k, _ in points)
        if sxx <= 0:
            continue
        slope = sum((k - mean_k) * (y - mean_y) for k, y in points) / sxx
        if -slope <= 0:
            continue
        estimates.append(-math.log(-slope) / t)
    if not estimates:
        return None
    rate = statistics.median(estimates)
    return rate if RATE_MIN <= rate <= RATE_MAX else None


_RATE_CACHE: tuple[float, RateInfo] | None = None


def _rate_file() -> Any:
    return auth.DATA_DIR / "rate.json"


def fetch_rate() -> RateInfo:
    """Market rate: from the S&P 500, at most every 6 hours; otherwise 4%.

    The S&P 500 file is large (over 10 MB): that is why the result is kept in
    memory and on disk instead of being downloaded again for every stock.
    """
    global _RATE_CACHE
    now = time.time()
    if _RATE_CACHE is not None and now - _RATE_CACHE[0] < RATE_CACHE_SECONDS:
        return _RATE_CACHE[1]
    try:
        saved = json.loads(_rate_file().read_text(encoding="utf-8"))
        if now - float(saved["saved"]) < RATE_CACHE_SECONDS:
            info = RateInfo(float(saved["rate"]), str(saved["source"]), str(saved["at"]))
            _RATE_CACHE = (float(saved["saved"]), info)
            return info
    except (OSError, ValueError, KeyError, TypeError):
        pass

    rate: float | None = None
    try:
        rate = implied_rate(fetch_chain(RATE_SYMBOL), date.today())
    except MarketDataError:
        rate = None
    stamp = datetime.now().strftime("%d/%m %H:%M")
    if rate is None:
        # No cache: the next stock tries again.
        return RateInfo(DEFAULT_RATE, RATE_DEFAULT, stamp)
    info = RateInfo(rate, RATE_FROM_SPX, stamp)
    _RATE_CACHE = (now, info)
    try:
        auth.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _rate_file().write_text(
            json.dumps({"rate": rate, "source": info.source, "at": stamp, "saved": now}),
            encoding="utf-8",
        )
    except OSError:
        pass
    return info


# ---------------------------------------------------------------------------
# Dividend
# ---------------------------------------------------------------------------


def implied_dividends(chain: Chain, rate: float, today: date) -> dict[date, float]:
    """Implied yield q for every expiry, from the forward at near-the-money strikes."""
    out: dict[date, float] = {}
    for expiry in chain.expiries:
        t = _years(expiry, today)
        if t <= 0:
            continue
        points = sorted(
            _pairs(chain, expiry, max_distance=0.15), key=lambda p: abs(p[0] - chain.spot)
        )[:NEAR_STRIKES]
        if not points:
            continue
        forward = statistics.median(k + diff * math.exp(rate * t) for k, diff in points)
        if forward <= 0:
            continue
        q = rate - math.log(forward / chain.spot) / t
        if abs(q) <= DIVIDEND_LIMIT:
            out[expiry] = q
    return out


def carry_for(chain: Chain, rate: RateInfo, today: date | None = None) -> Carry:
    return Carry(
        rate=rate,
        dividends=implied_dividends(chain, rate.rate, today or date.today()),
        exercise=exercise_style(chain.ticker),
    )


# ---------------------------------------------------------------------------
# Check: do calls and puts agree?
# ---------------------------------------------------------------------------


def parity_check(chain: Chain, carry: Carry, today: date | None = None) -> ParityCheck | None:
    """Compare call and put IV on the same strike, before and after.

    Before = 4% rate and zero dividend; after = derived values. It looks at the
    four strikes nearest the price, on expiries between 2 weeks and a year:
    that is where quotes are most reliable.
    """
    day = today or date.today()
    before: list[float] = []
    after: list[float] = []
    for expiry in chain.expiries:
        days = (expiry - day).days
        if not 14 <= days <= 365:
            continue
        strikes = sorted(chain.strikes(expiry), key=lambda k: abs(k - chain.spot))[:NEAR_STRIKES]
        for strike in strikes:
            call = chain.quote(expiry, "call", strike)
            put = chain.quote(expiry, "put", strike)
            if call is None or put is None or call.bid <= 0 or put.bid <= 0:
                continue
            if call.mid is None or put.mid is None:
                continue
            for target, rate, q in (
                (before, DEFAULT_RATE, 0.0),
                (after, carry.rate.rate, carry.dividend(expiry)),
            ):
                base = {
                    "spot": chain.spot,
                    "strike": strike,
                    "days_to_expiry": float(days),
                    "risk_free_rate": rate,
                    "iv": 0.2,
                    "dividend_yield": q,
                }
                iv_call = implied_volatility(
                    call.mid, OptionSpec(right="call", **base), carry.exercise
                )
                iv_put = implied_volatility(
                    put.mid, OptionSpec(right="put", **base), carry.exercise
                )
                if iv_call is not None and iv_put is not None:
                    target.append(abs(iv_call - iv_put) * 100)
    if not before or not after:
        return None
    return ParityCheck(
        before=statistics.median(before),
        after=statistics.median(after),
        pairs=len(after),
    )
