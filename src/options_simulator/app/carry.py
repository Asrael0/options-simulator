"""Tasso e dividendo ricavati dai prezzi delle opzioni.

--- COSA FA QUESTO FILE ---
Il modello ha bisogno di due numeri che il mercato non scrive da nessuna
parte: il tasso privo di rischio e il dividendo del titolo. Metterli a caso (4%
e 0%) sbaglia i prezzi, soprattutto per i titoli che pagano dividendi alti.
Qui li si ricava dalle opzioni stesse, con la PUT-CALL PARITY.

L'IDEA. Una call comprata e una put venduta allo stesso strike K fanno, a
scadenza, esattamente come avere il titolo e dover pagare K. Quindi oggi:

    C − P = S·e^(−qT) − K·e^(−rT)        (opzioni europee)

  - TASSO: al variare di K, C − P scende di e^(−rT) per ogni dollaro di
    strike. La pendenza della retta dà r. Lo si fa sulle opzioni dell'S&P 500
    (indice ``_SPX``), che sono europee: lì la formula vale esattamente.
  - DIVIDENDO: noto r, da C − P agli strike vicini al prezzo si ottiene il
    forward F = K + (C − P)·e^(rT), e da lì q = r − ln(F/S)/T, scadenza per
    scadenza. Sulle azioni americane si usano solo gli strike vicini al
    prezzo, dove l'esercizio anticipato pesa poco.

Il "dividendo" così ricavato è in realtà tutto ciò che separa il forward dallo
spot: dividendi, costo di prestito del titolo per chi lo vende allo scoperto,
piccoli disallineamenti fra prezzi. Per questo nell'interfaccia si chiama
«rendimento implicito».

LA VERIFICA. Con tasso e dividendo giusti, una call e una put allo stesso
strike devono avere la stessa volatilità implicita. ``parity_check`` misura
quanto differiscono prima e dopo: è il modo onesto di sapere se i numeri
ricavati migliorano davvero il modello.
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
DIVIDEND_LIMIT = 0.5  # oltre ±50% annuo il dato è sicuramente rotto

NEAR_STRIKES = 4
MAX_SPREAD = 0.30


@dataclass(frozen=True, slots=True)
class RateInfo:
    rate: float
    source: str  # testo da mostrare: da dove viene il tasso
    measured_at: str


@dataclass(frozen=True, slots=True)
class Carry:
    """Tasso del mercato e rendimento implicito del titolo, per scadenza."""

    rate: RateInfo
    dividends: dict[date, float]
    exercise: ExerciseStyle

    def dividend(self, expiry: date) -> float:
        return self.dividends.get(expiry, self.dividend_yield or 0.0)

    @property
    def dividend_yield(self) -> float | None:
        """Valore riassuntivo: mediana sulle scadenze fra 1 mese e 1 anno e mezzo.

        Le scadenze brevissime sono troppo rumorose (pochi giorni amplificano
        ogni centesimo di errore) e risentono del singolo stacco di dividendo.
        """
        today = date.today()
        middle = [q for e, q in self.dividends.items() if 30 <= (e - today).days <= 580]
        values = middle or list(self.dividends.values())
        return statistics.median(values) if values else None


@dataclass(frozen=True, slots=True)
class ParityCheck:
    """Differenza mediana fra IV di call e put allo stesso strike, in punti %."""

    before: float  # con tasso predefinito e dividendo zero
    after: float  # con tasso e dividendo ricavati
    pairs: int


def exercise_style(ticker: str) -> ExerciseStyle:
    """Le opzioni sugli indici (simboli con «_») sono europee, le altre americane."""
    return "european" if is_index(ticker) else "american"


def _years(expiry: date, today: date) -> float:
    return (expiry - today).days / 365.0


def _pairs(chain: Chain, expiry: date, *, max_distance: float) -> list[tuple[float, float]]:
    """(strike, C − P) per gli strike con call e put entrambe quotate e liquide."""
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
# Tasso
# ---------------------------------------------------------------------------


def implied_rate(chain: Chain, today: date) -> float | None:
    """Tasso dalla pendenza di C − P rispetto allo strike (solo opzioni europee).

    Una retta per scadenza; si tiene la mediana delle scadenze fra 2 mesi e
    2 anni e mezzo, dove la stima è stabile.
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
    return auth.DATA_DIR / "tasso.json"


def fetch_rate() -> RateInfo:
    """Tasso di mercato: dall'S&P 500, al massimo ogni 6 ore; altrimenti il 4%.

    Il file dell'S&P 500 è grande (oltre 10 MB): per questo il risultato si
    conserva in memoria e su disco, e non si riscarica a ogni titolo.
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
        # Niente cache: al prossimo titolo si riprova.
        return RateInfo(DEFAULT_RATE, "valore predefinito (S&P 500 non disponibile)", stamp)
    info = RateInfo(rate, "ricavato dalle opzioni sull'S&P 500", stamp)
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
# Dividendo
# ---------------------------------------------------------------------------


def implied_dividends(chain: Chain, rate: float, today: date) -> dict[date, float]:
    """Rendimento implicito q per ogni scadenza, dal forward agli strike vicini al prezzo."""
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
# Verifica: call e put concordano?
# ---------------------------------------------------------------------------


def parity_check(chain: Chain, carry: Carry, today: date | None = None) -> ParityCheck | None:
    """Confronta la IV di call e put allo stesso strike, prima e dopo.

    Prima = tasso 4% e dividendo zero; dopo = valori ricavati. Si guardano i
    quattro strike più vicini al prezzo delle scadenze fra 2 settimane e un
    anno: lì le quotazioni sono le più affidabili.
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
