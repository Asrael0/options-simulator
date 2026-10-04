"""Historical against implied volatility: are options expensive or cheap?

IMPLIED volatility (IV) is what the market puts into option prices: a forecast
of how much the stock will move. HISTORICAL volatility (HV) is how much the
stock really moved, measured on past prices.

Comparing them answers the first question of anyone trading options:
  - IV well above HV  -> the market charges a lot for future movement: options
    are "expensive", selling them is more attractive;
  - IV below HV       -> options are "cheap", buying them costs little compared
    with how much the stock is moving.

HOW HV IS COMPUTED. For each day take the log return ln(P_today / P_yesterday);
the standard deviation of those returns over a window (20 days, 60, a year) is
annualised by multiplying by √252, the number of trading days in a year. It is
exactly the quantity IV tries to predict.

DATA. The daily history comes from CBOE (the same source as the options). CBOE
does not provide it for indices: the ETF tracking them is used instead (SPY for
the S&P 500…), and the page says so. For the VIX the comparison makes no sense:
the VIX already IS an implied volatility.

CAVEAT. IV usually sits a little above HV even in normal conditions: option
sellers ask for a premium for the risk of sudden moves. And before an event
(quarterly earnings) IV rises on purpose. "Expensive" does not mean "wrong".
"""

from __future__ import annotations

import itertools
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from .market_data import MarketDataError
from .tickers import canonical_symbol, display_symbol, is_index

HISTORY_URL = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/{symbol}.json"
HISTORY_CACHE_SECONDS = 6 * 3600
TRADING_DAYS = 252
TIMEOUT_SECONDS = 20

# Indices without history on CBOE: use the ETF that tracks them.
INDEX_PROXIES = {
    "SPX": "SPY",
    "XSP": "SPY",
    "NDX": "QQQ",
    "XND": "QQQ",
    "RUT": "IWM",
    "MRUT": "IWM",
    "DJX": "DIA",
    "OEX": "OEF",
    "XEO": "OEF",
    "SPXW": "SPY",
}

Verdict = Literal["expensive", "average", "cheap"]


@dataclass(frozen=True, slots=True)
class PricePoint:
    day: date
    close: float


@dataclass(frozen=True, slots=True)
class VolatilityReport:
    """Everything the «Volatility» tab needs."""

    source: str  # symbol the history comes from (different for indices)
    prices: list[PricePoint]  # roughly the last year, for the chart
    rolling: list[tuple[date, float]]  # 30-day HV, day by day
    hv20: float
    hv60: float
    hv252: float
    iv: float | None
    percentile: float | None  # share of last year's days with HV30 < IV
    ratio: float | None  # IV / 20-day HV
    verdict: Verdict | None


# ---------------------------------------------------------------------------
# Calculations (pure functions, testable without internet)
# ---------------------------------------------------------------------------


def log_returns(closes: list[float]) -> list[float]:
    return [math.log(b / a) for a, b in itertools.pairwise(closes) if a > 0 and b > 0]


def realized_volatility(closes: list[float], window: int) -> float | None:
    """Annualised historical volatility of the last ``window`` returns."""
    returns = log_returns(closes[-(window + 1) :])
    if len(returns) < max(2, window // 2):
        return None
    return statistics.stdev(returns) * math.sqrt(TRADING_DAYS)


def rolling_volatility(
    points: list[PricePoint], window: int = 30, keep: int = TRADING_DAYS
) -> list[tuple[date, float]]:
    """``window``-day HV computed every day, for the last ``keep`` days."""
    closes = [p.close for p in points]
    returns = log_returns(closes)
    out: list[tuple[date, float]] = []
    start = max(window, len(returns) - keep)
    for end in range(start, len(returns) + 1):
        chunk = returns[end - window : end]
        if len(chunk) == window:
            out.append((points[end].day, statistics.stdev(chunk) * math.sqrt(TRADING_DAYS)))
    return out


def verdict_for(ratio: float | None) -> Verdict | None:
    """Expensive when IV exceeds recent HV by over 25%, cheap when it is 10% below.

    The thresholds are asymmetric on purpose: IV normally sits a little above HV
    (the risk premium option sellers ask for), so a slightly higher IV is
    "average", not "expensive".
    """
    if ratio is None:
        return None
    if ratio >= 1.25:
        return "expensive"
    if ratio <= 0.90:
        return "cheap"
    return "average"


def build_report(points: list[PricePoint], iv: float | None, source: str) -> VolatilityReport:
    closes = [p.close for p in points]
    hv20 = realized_volatility(closes, 20)
    hv60 = realized_volatility(closes, 60)
    hv252 = realized_volatility(closes, TRADING_DAYS)
    if hv20 is None or hv60 is None:
        raise MarketDataError("Storico troppo corto per calcolare la volatilità.")
    rolling = rolling_volatility(points)
    percentile = (
        sum(1 for _, hv in rolling if hv < iv) / len(rolling)
        if iv is not None and rolling
        else None
    )
    ratio = iv / hv20 if iv is not None and hv20 > 0 else None
    return VolatilityReport(
        source=source,
        prices=points[-TRADING_DAYS:],
        rolling=rolling,
        hv20=hv20,
        hv60=hv60,
        hv252=hv252 if hv252 is not None else hv60,
        iv=iv,
        percentile=percentile,
        ratio=ratio,
        verdict=verdict_for(ratio),
    )


def parse_history(payload: Any) -> list[PricePoint]:
    try:
        rows = payload["data"]
        points = [
            PricePoint(date.fromisoformat(str(row["date"])), float(row["close"]))
            for row in rows
            if row.get("close")
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise MarketDataError("Lo storico di CBOE non ha il formato atteso.") from error
    return sorted(points, key=lambda p: p.day)


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[float, list[PricePoint]]] = {}


def history_symbol(ticker: str) -> str | None:
    """Symbol to download the history for; ``None`` when it makes no sense (VIX)."""
    plain = display_symbol(ticker)
    if plain == "VIX":
        return None
    if is_index(ticker):
        return INDEX_PROXIES.get(plain)
    return canonical_symbol(ticker)


def fetch_history(symbol: str) -> list[PricePoint]:
    cached = _CACHE.get(symbol)
    if cached is not None and time.monotonic() - cached[0] < HISTORY_CACHE_SECONDS:
        return cached[1]
    request = urllib.request.Request(
        HISTORY_URL.format(symbol=symbol),
        headers={"User-Agent": "Mozilla/5.0 (options-simulator, personal use)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise MarketDataError(
                "CBOE ha ricevuto troppe richieste: riprova fra qualche minuto."
            ) from error
        raise MarketDataError("Storico non disponibile per {symbol}.", symbol=symbol) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise MarketDataError("Impossibile raggiungere CBOE per lo storico.") from error
    if not body:
        raise MarketDataError("CBOE non fornisce lo storico di {symbol}.", symbol=symbol)
    try:
        points = parse_history(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MarketDataError("Lo storico di CBOE è illeggibile.") from error
    _CACHE[symbol] = (time.monotonic(), points)
    return points


def volatility_report(ticker: str, iv: float | None) -> VolatilityReport:
    """Download the history and compare realised volatility with ``iv``."""
    symbol = history_symbol(ticker)
    if symbol is None:
        raise MarketDataError(
            "Il VIX è già una volatilità implicita: il confronto con la storica non si applica."
        )
    return build_report(fetch_history(symbol), iv, symbol)
