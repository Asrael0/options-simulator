"""Opzioni reali: scarica e interpreta la catena di un titolo dal sito CBOE.

--- COSA FA QUESTO FILE ---
È l'unico punto in cui il simulatore va su internet. Scarica un file JSON
pubblico di CBOE (la principale borsa di opzioni americana) che contiene, per
un titolo USA, il prezzo corrente e tutte le opzioni quotate: prezzi denaro e
lettera, volatilità implicita, greche, interesse aperto.

Due parti separate apposta:
  - ``fetch_chain`` fa la richiesta di rete (lenta, può fallire);
  - ``parse_chain`` trasforma il JSON in oggetti Python. È una funzione pura:
    si può provare nei test senza internet.

AVVERTENZE
- I dati sono in RITARDO di circa 15 minuti e vanno usati a scopo personale e
  di studio. Non sono un servizio garantito: CBOE può cambiare il formato o
  l'indirizzo senza preavviso, e in quel caso qui si vedrà un errore chiaro.
- Solo titoli e indici USA (AAPL, SPY, TSLA…). Per gli indici come SPX il
  simbolo va scritto con il trattino basso davanti: ``_SPX``.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ..pricing import (
    ExerciseStyle,
    Leg,
    ManualPremium,
    MarketParams,
    OptionLeg,
    OptionSpec,
    Right,
    Side,
    price_option,
)
from .i18n import tr
from .state import PositionState
from .strategies import CUSTOM_STRATEGY, new_leg_id
from .tickers import canonical_symbol, company_name, display_symbol

SOURCE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
SOURCE_NAME = "CBOE (dati in ritardo di 15 minuti)"
CACHE_SECONDS = 60
TIMEOUT_SECONDS = 20


class MarketDataError(Exception):
    """Errore con un messaggio da mostrare all'utente.

    Il messaggio è un modello italiano con segnaposto, tradotto solo quando lo
    si mostra (``str(errore)``): chi lo solleva gira in un thread che non sa
    quale lingua abbia scelto il visitatore.
    """

    def __init__(self, message: str, **values: object) -> None:
        super().__init__(message)
        self.message = message
        self.values = values

    def __str__(self) -> str:
        return tr(self.message, **self.values)


@dataclass(frozen=True, slots=True)
class Quote:
    """Una singola opzione quotata."""

    right: Right
    strike: float
    expiry: date
    bid: float
    ask: float
    last: float
    iv: float | None
    delta: float | None
    open_interest: float
    volume: float

    @property
    def mid(self) -> float | None:
        """Prezzo «giusto» di mercato: a metà fra denaro e lettera."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        if self.ask > 0:
            return self.ask / 2
        return self.last if self.last > 0 else None

    @property
    def spread_pct(self) -> float | None:
        """Larghezza dello spread rispetto al mid: indica quanto è liquida."""
        mid = self.mid
        if mid is None or mid <= 0 or self.bid <= 0:
            return None
        return (self.ask - self.bid) / mid


@dataclass(frozen=True, slots=True)
class Chain:
    """La catena completa di un titolo."""

    ticker: str
    spot: float
    change_pct: float
    iv30: float | None
    quoted_at: str
    quotes: dict[date, list[Quote]]

    @property
    def expiries(self) -> list[date]:
        return sorted(self.quotes)

    def strikes(self, expiry: date) -> list[float]:
        return sorted({q.strike for q in self.quotes.get(expiry, [])})

    def quote(self, expiry: date, right: Right, strike: float) -> Quote | None:
        return next(
            (
                q
                for q in self.quotes.get(expiry, [])
                if q.right == right and abs(q.strike - strike) < 1e-9
            ),
            None,
        )

    def atm_iv(self, expiry: date) -> float | None:
        """Volatilità implicita allo strike più vicino al prezzo (media call/put)."""
        strikes = self.strikes(expiry)
        if not strikes:
            return None
        nearest = min(strikes, key=lambda k: abs(k - self.spot))
        ivs = [
            q.iv
            for right in ("call", "put")
            if (q := self.quote(expiry, right, nearest)) is not None and q.iv
        ]
        return sum(ivs) / len(ivs) if ivs else self.iv30


# ---------------------------------------------------------------------------
# Interpretazione del JSON
# ---------------------------------------------------------------------------


def _parse_symbol(symbol: str) -> tuple[date, Right, float]:
    """Simbolo OCC, es. ``AAPL261016C00230000``: data, tipo, strike.

    Gli ultimi 15 caratteri hanno sempre lo stesso formato: AAMMGG, C o P,
    strike moltiplicato per 1000 su otto cifre. Ciò che sta prima è la radice
    del titolo, che può variare (``SPXW`` per le settimanali sull'S&P 500).
    """
    tail = symbol[-15:]
    expiry = datetime.strptime(tail[:6], "%y%m%d").date()
    right: Right = "call" if tail[6] == "C" else "put"
    return expiry, right, int(tail[7:]) / 1000


def _number(raw: Any) -> float:
    try:
        return float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0


def parse_chain(payload: Any, today: date) -> Chain:
    """Trasforma il JSON di CBOE in una ``Chain``. Scarta le scadenze passate."""
    try:
        data = payload["data"]
        spot = _number(data.get("current_price")) or _number(data.get("close"))
        options = data["options"]
    except (KeyError, TypeError) as error:
        raise MarketDataError("Il formato dei dati CBOE non è quello atteso.") from error
    if spot <= 0:
        raise MarketDataError("CBOE non ha restituito un prezzo valido per questo titolo.")

    quotes: dict[date, list[Quote]] = {}
    for raw in options:
        try:
            expiry, right, strike = _parse_symbol(str(raw["option"]))
        except (KeyError, ValueError, IndexError):
            continue
        if expiry <= today:
            continue
        iv = _number(raw.get("iv"))
        quotes.setdefault(expiry, []).append(
            Quote(
                right=right,
                strike=strike,
                expiry=expiry,
                bid=_number(raw.get("bid")),
                ask=_number(raw.get("ask")),
                last=_number(raw.get("last_trade_price")),
                iv=iv if iv > 0 else None,
                delta=_number(raw.get("delta")) if raw.get("delta") is not None else None,
                open_interest=_number(raw.get("open_interest")),
                volume=_number(raw.get("volume")),
            )
        )
    if not quotes:
        raise MarketDataError("Nessuna opzione con scadenza futura per questo titolo.")

    iv30 = _number(data.get("iv30"))
    return Chain(
        # CBOE restituisce gli indici come «^SPX»: si riporta alla forma interna.
        ticker=canonical_symbol(str(data.get("symbol") or payload.get("symbol") or "")),
        spot=spot,
        change_pct=_number(data.get("price_change_percent")) / 100,
        iv30=iv30 / 100 if iv30 > 0 else None,
        quoted_at=str(payload.get("timestamp") or ""),
        quotes=quotes,
    )


# ---------------------------------------------------------------------------
# Rete
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[float, Chain]] = {}


def normalize_ticker(ticker: str) -> str:
    """Maiuscolo, senza spazi; accetta solo i caratteri ammessi nei simboli."""
    cleaned = ticker.strip().upper()
    if not cleaned or len(cleaned) > 10 or not all(c.isalnum() or c in "_.^$" for c in cleaned):
        raise MarketDataError("Scrivi un simbolo valido, per esempio AAPL o SPY.")
    return canonical_symbol(cleaned)


def fetch_chain(ticker: str) -> Chain:
    """Scarica la catena del titolo. Bloccante: va chiamata fuori dall'interfaccia."""
    symbol = normalize_ticker(ticker)
    cached = _CACHE.get(symbol)
    if cached is not None and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    request = urllib.request.Request(
        SOURCE_URL.format(symbol=symbol),
        headers={"User-Agent": "Mozilla/5.0 (options-simulator, uso personale)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code in (403, 404):
            raise MarketDataError(
                "CBOE non ha opzioni per «{symbol}»: funziona solo con titoli, ETF e indici USA.",
                symbol=display_symbol(symbol),
            ) from error
        if error.code == 429:
            raise MarketDataError(
                "CBOE ha ricevuto troppe richieste e ci ha messo in pausa: "
                "riprova fra qualche minuto."
            ) from error
        raise MarketDataError(
            "CBOE ha risposto con un errore ({code}).", code=error.code
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise MarketDataError(
            "Impossibile raggiungere CBOE: controlla la connessione a internet."
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MarketDataError("CBOE ha restituito dati illeggibili.") from error

    chain = parse_chain(payload, date.today())
    _CACHE[symbol] = (time.monotonic(), chain)
    return chain


# ---------------------------------------------------------------------------
# Modello contro mercato
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModelRow:
    """Una riga del confronto: lo stesso strike, prezzo di mercato e del modello."""

    strike: float
    call_market: float | None
    call_model: float
    call_iv: float | None
    put_market: float | None
    put_model: float
    put_iv: float | None


def model_vs_market(
    chain: Chain,
    expiry: date,
    *,
    iv: float,
    risk_free_rate: float,
    dividend_yield: float,
    exercise: ExerciseStyle,
    today: date | None = None,
) -> list[ModelRow]:
    """Prezza ogni strike con UNA sola volatilità e lo affianca al mercato.

    È il confronto più istruttivo: il modello usa la stessa IV per tutti gli
    strike, il mercato no. Lo scarto che ne esce, strike per strike, è il
    «sorriso» (o la smorfia) della volatilità.
    """
    days = (expiry - (today or date.today())).days
    rows: list[ModelRow] = []
    for strike in chain.strikes(expiry):
        prices: dict[str, float] = {}
        for right in ("call", "put"):
            spec = OptionSpec(
                spot=chain.spot,
                strike=strike,
                days_to_expiry=days,
                risk_free_rate=risk_free_rate,
                iv=iv,
                right=right,
                dividend_yield=dividend_yield,
            )
            prices[right] = price_option(spec, exercise, "curve")
        call = chain.quote(expiry, "call", strike)
        put = chain.quote(expiry, "put", strike)
        rows.append(
            ModelRow(
                strike=strike,
                call_market=call.mid if call else None,
                call_model=prices["call"],
                call_iv=call.iv if call else None,
                put_market=put.mid if put else None,
                put_model=prices["put"],
                put_iv=put.iv if put else None,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Dalla catena al simulatore
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BasketLeg:
    """Un'opzione scelta dalla catena, in attesa di andare nel simulatore."""

    right: Right
    side: Side
    strike: float
    qty: float
    premium: float
    iv: float | None


def position_from_basket(
    chain: Chain,
    expiry: date,
    basket: list[BasketLeg],
    *,
    risk_free_rate: float,
    dividend_yield: float = 0.0,
    exercise: ExerciseStyle = "american",
    today: date | None = None,
) -> PositionState:
    """Costruisce la posizione del simulatore con dati e prezzi veri.

    - spot, giorni alla scadenza e IV (quella ATM della scadenza) vengono dal
      mercato;
    - il premio d'ingresso di ogni gamba è il mid di mercato, imposto a mano:
      è quanto si pagherebbe davvero, non il prezzo del modello;
    - tasso e dividendo sono quelli ricavati dalla catena (vedi ``carry.py``);
    - lo stile è americano per le azioni USA, europeo per gli indici.
    """
    days = float((expiry - (today or date.today())).days)
    iv = chain.atm_iv(expiry) or chain.iv30 or 0.3
    market = MarketParams(
        spot=chain.spot,
        days_to_expiry=days,
        risk_free_rate=risk_free_rate,
        iv=iv,
        dividend_yield=dividend_yield,
    )
    legs: list[Leg] = [
        OptionLeg(
            leg_id=new_leg_id(),
            side=leg.side,
            qty=leg.qty,
            right=leg.right,
            strike=leg.strike,
            premium=ManualPremium(round(leg.premium, 4)),
        )
        for leg in basket
    ]
    return PositionState(
        ticker=display_symbol(chain.ticker),
        name=company_name(chain.ticker) or display_symbol(chain.ticker),
        market=market,
        entry_market=market,
        pin_premiums=True,
        exercise=exercise,
        legs=legs,
        strategy_key=CUSTOM_STRATEGY,
        target=chain.spot,
        iv_sim=iv,
    )
