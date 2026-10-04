"""Volatilità storica contro implicita: le opzioni sono care o economiche?

--- COSA FA QUESTO FILE ---
La volatilità IMPLICITA (IV) è quella che il mercato mette nei prezzi delle
opzioni: una previsione di quanto si muoverà il titolo. La volatilità STORICA
(HV) è quanto il titolo si è mosso davvero, misurata sui prezzi passati.

Metterle a confronto risponde alla prima domanda di chi tratta opzioni:
  - IV molto sopra la HV  -> il mercato fa pagare caro il movimento futuro:
    le opzioni sono "care", venderle è più interessante;
  - IV sotto la HV        -> le opzioni sono "economiche", comprarle costa
    poco rispetto a quanto il titolo si sta muovendo.

COME SI CALCOLA LA HV. Per ogni giorno si prende il rendimento logaritmico
ln(P_oggi / P_ieri); la deviazione standard di quei rendimenti su una
finestra (20 giorni, 60, un anno) si annualizza moltiplicando per √252, il
numero di giorni di borsa in un anno. È esattamente la grandezza che la IV
prova a prevedere.

DATI. Lo storico giornaliero viene da CBOE (stessa fonte delle opzioni). Per
gli indici CBOE non lo fornisce: si usa l'ETF che li replica (SPY per l'S&P
500…), e la pagina lo dice. Per il VIX il confronto non ha senso: il VIX È già
una volatilità implicita.

ATTENZIONE. La IV sta di solito un po' sopra la HV anche in condizioni
normali: chi vende opzioni chiede un premio per il rischio di movimenti
improvvisi. E prima di un evento (utili trimestrali) la IV sale apposta.
"Cara" non vuol dire "sbagliata".
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

# Indici senza storico su CBOE: si usa l'ETF che li replica.
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

Verdict = Literal["care", "nella media", "economiche"]


@dataclass(frozen=True, slots=True)
class PricePoint:
    day: date
    close: float


@dataclass(frozen=True, slots=True)
class VolatilityReport:
    """Tutto ciò che serve alla scheda «Volatilità»."""

    source: str  # simbolo da cui viene lo storico (diverso per gli indici)
    prices: list[PricePoint]  # ultimo anno circa, per il grafico
    rolling: list[tuple[date, float]]  # HV a 30 giorni, giorno per giorno
    hv20: float
    hv60: float
    hv252: float
    iv: float | None
    percentile: float | None  # quota di giorni dell'ultimo anno con HV30 < IV
    ratio: float | None  # IV / HV a 20 giorni
    verdict: Verdict | None


# ---------------------------------------------------------------------------
# Calcoli (funzioni pure: si provano senza internet)
# ---------------------------------------------------------------------------


def log_returns(closes: list[float]) -> list[float]:
    return [math.log(b / a) for a, b in itertools.pairwise(closes) if a > 0 and b > 0]


def realized_volatility(closes: list[float], window: int) -> float | None:
    """Volatilità storica annualizzata degli ultimi ``window`` rendimenti."""
    returns = log_returns(closes[-(window + 1) :])
    if len(returns) < max(2, window // 2):
        return None
    return statistics.stdev(returns) * math.sqrt(TRADING_DAYS)


def rolling_volatility(
    points: list[PricePoint], window: int = 30, keep: int = TRADING_DAYS
) -> list[tuple[date, float]]:
    """HV a ``window`` giorni calcolata ogni giorno, per gli ultimi ``keep`` giorni."""
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
    """Care se la IV supera di oltre il 25% la HV recente, economiche se è sotto del 10%.

    Le soglie sono asimmetriche apposta: la IV sta normalmente un po' sopra la
    HV (il premio per il rischio di chi vende opzioni), quindi una IV appena
    più alta è "nella media", non "cara".
    """
    if ratio is None:
        return None
    if ratio >= 1.25:
        return "care"
    if ratio <= 0.90:
        return "economiche"
    return "nella media"


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
# Rete
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[float, list[PricePoint]]] = {}


def history_symbol(ticker: str) -> str | None:
    """Simbolo da cui scaricare lo storico; ``None`` se non ha senso (VIX)."""
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
        headers={"User-Agent": "Mozilla/5.0 (options-simulator, uso personale)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise MarketDataError(
                "CBOE ha ricevuto troppe richieste: riprova fra qualche minuto."
            ) from error
        raise MarketDataError(f"Storico non disponibile per {symbol}.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise MarketDataError("Impossibile raggiungere CBOE per lo storico.") from error
    if not body:
        raise MarketDataError(f"CBOE non fornisce lo storico di {symbol}.")
    try:
        points = parse_history(json.loads(body.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MarketDataError("Lo storico di CBOE è illeggibile.") from error
    _CACHE[symbol] = (time.monotonic(), points)
    return points


def volatility_report(ticker: str, iv: float | None) -> VolatilityReport:
    """Scarica lo storico e confronta la volatilità realizzata con ``iv``."""
    symbol = history_symbol(ticker)
    if symbol is None:
        raise MarketDataError(
            "Il VIX è già una volatilità implicita: il confronto con la storica non si applica."
        )
    return build_report(fetch_history(symbol), iv, symbol)
