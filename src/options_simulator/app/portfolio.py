"""Portafoglio virtuale: posizioni aperte "per finta" ai prezzi veri.

--- COSA FA QUESTO FILE ---
Chiude il cerchio dell'apprendimento. Il simulatore dice cosa *dovrebbe*
succedere; qui si apre una posizione ai prezzi reali di oggi, si torna nei
giorni seguenti e si vede cosa è successo davvero.

Per ogni posizione si conserva:
  - COSA si è fatto: le gambe, ai prezzi realmente pagati o incassati (chi
    compra paga la lettera, chi vende incassa il denaro);
  - COSA PREVEDEVA IL MODELLO in quel momento: probabilità di profitto,
    break-even, guadagno e perdita massimi;
  - COME È ANDATA: un punto al giorno con prezzo del titolo e valore della
    posizione, fino alla chiusura.

Tutto in ``~/.options-simulator/portafoglio.json``, separato per utente.

VALORI IN DOLLARI VERI. A differenza del simulatore, che ragiona "per azione",
qui ogni cifra è già moltiplicata per il moltiplicatore del contratto (100
azioni) e per il numero di contratti: è quanto si avrebbe sul conto.

LIMITI, detti chiaramente:
  - nessuna commissione e nessun margine;
  - nessun esercizio anticipato né assegnazione prima della scadenza;
  - una posizione scaduta si regola al valore intrinseco calcolato sul prezzo
    del titolo del giorno in cui la si aggiorna, che può essere successivo
    alla scadenza: è un'approssimazione, segnalata a schermo.
"""

from __future__ import annotations

import json
import secrets
import statistics
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

from ..pricing import OptionSpec, price_option
from . import auth
from .i18n import tr
from .market_data import BasketLeg, Chain, Quote, position_from_basket
from .state import compute
from .tickers import company_name, display_symbol

MULTIPLIER = 100.0
MAX_OPEN = 100

Status = Literal["open", "closed"]


@dataclass(frozen=True, slots=True)
class PaperLeg:
    right: str  # "call" | "put"
    side: str  # "long" | "short"
    strike: float
    contracts: float
    entry_price: float  # per azione, quello davvero pagato o incassato

    @property
    def sign(self) -> float:
        return 1.0 if self.side == "long" else -1.0


@dataclass(frozen=True, slots=True)
class Snapshot:
    day: str  # ISO, uno per giorno
    spot: float
    value: float  # valore della posizione in $ (mark al mid)


@dataclass(frozen=True, slots=True)
class Forecast:
    """La previsione del modello al momento dell'apertura (in $ veri)."""

    prob_profit: float
    break_evens: list[float]
    max_profit: float | None  # None = illimitato
    max_loss: float | None


@dataclass(frozen=True, slots=True)
class PaperPosition:
    position_id: str
    ticker: str  # forma interna (``_SPX``)
    name: str
    expiry: str  # ISO
    opened_at: str  # ISO con ora
    entry_spot: float
    entry_iv: float
    rate: float
    dividend: float
    exercise: str
    legs: list[PaperLeg]
    forecast: Forecast
    note: str = ""
    status: Status = "open"
    snapshots: list[Snapshot] = field(default_factory=list)
    last_value: float | None = None
    last_spot: float | None = None
    last_iv: float | None = None
    last_update: str | None = None
    closed_at: str | None = None
    exit_value: float | None = None
    settled_at_expiry: bool = False

    # -- valori derivati ---------------------------------------------------

    @property
    def expiry_date(self) -> date:
        return date.fromisoformat(self.expiry)

    @property
    def entry_cost(self) -> float:
        """$ pagati (positivo) o incassati (negativo) all'apertura."""
        return sum(leg.sign * leg.entry_price * leg.contracts for leg in self.legs) * MULTIPLIER

    @property
    def current_value(self) -> float | None:
        return self.exit_value if self.status == "closed" else self.last_value

    @property
    def pl(self) -> float | None:
        """Guadagno o perdita in $: valore attuale (o di chiusura) meno costo."""
        value = self.current_value
        return None if value is None else value - self.entry_cost

    @property
    def pl_pct(self) -> float | None:
        pl = self.pl
        if pl is None or abs(self.entry_cost) < 1e-9:
            return None
        return pl / abs(self.entry_cost)

    @property
    def display_ticker(self) -> str:
        return display_symbol(self.ticker)

    def describe(self) -> str:
        """Riassunto delle gambe, es. «Long 1 call 335 · Short 1 call 345»."""
        return " · ".join(
            f"{leg.side.title()} {leg.contracts:g} {leg.right} {leg.strike:g}" for leg in self.legs
        )


# ---------------------------------------------------------------------------
# Lettura e scrittura
# ---------------------------------------------------------------------------


def _file() -> Path:
    return auth.DATA_DIR / "portafoglio.json"


def _from_raw(raw: dict[str, Any]) -> PaperPosition:
    data = dict(raw)
    data["legs"] = [PaperLeg(**leg) for leg in data["legs"]]
    data["snapshots"] = [Snapshot(**snap) for snap in data.get("snapshots", [])]
    data["forecast"] = Forecast(**data["forecast"])
    return PaperPosition(**data)


def _load_all() -> dict[str, list[dict[str, Any]]]:
    try:
        raw: Any = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_all(payload: dict[str, list[dict[str, Any]]]) -> None:
    auth.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_for(username: str) -> list[PaperPosition]:
    """Posizioni dell'utente: prima le aperte, poi le chiuse, dalla più recente."""
    items: list[PaperPosition] = []
    for raw in _load_all().get(username, []):
        try:
            items.append(_from_raw(raw))
        except (KeyError, TypeError, ValueError):
            continue
    newest_first = sorted(items, key=lambda p: p.opened_at, reverse=True)
    return sorted(newest_first, key=lambda p: p.status != "open")


def _store(username: str, positions: list[PaperPosition]) -> None:
    payload = _load_all()
    payload[username] = [asdict(p) for p in positions]
    _save_all(payload)


def _replace(username: str, updated: PaperPosition) -> None:
    positions = [updated if p.position_id == updated.position_id else p for p in list_for(username)]
    _store(username, positions)


def delete(username: str, position_id: str) -> None:
    _store(username, [p for p in list_for(username) if p.position_id != position_id])


# ---------------------------------------------------------------------------
# Apertura
# ---------------------------------------------------------------------------


def open_position(
    username: str,
    chain: Chain,
    expiry: date,
    basket: list[BasketLeg],
    *,
    rate: float,
    dividend: float,
    exercise: str,
    note: str = "",
    today: date | None = None,
) -> PaperPosition:
    """Registra la posizione ai prezzi del carrello e la previsione del modello."""
    day = today or date.today()
    if not basket:
        raise ValueError(tr("Nessuna opzione scelta."))
    if sum(1 for p in list_for(username) if p.status == "open") >= MAX_OPEN:
        raise ValueError(tr("Hai già {n} posizioni aperte: chiudine qualcuna.", n=MAX_OPEN))

    state = position_from_basket(
        chain,
        expiry,
        list(basket),
        risk_free_rate=rate,
        dividend_yield=dividend,
        exercise=exercise,  # type: ignore[arg-type]
        today=day,
    )
    analytics = compute(state)

    def dollars(value: float, unbounded: bool) -> float | None:
        return None if unbounded else value * MULTIPLIER

    now = datetime.now(UTC).isoformat(timespec="seconds")
    position = PaperPosition(
        position_id=secrets.token_hex(6),
        ticker=chain.ticker,
        name=company_name(chain.ticker) or display_symbol(chain.ticker),
        expiry=expiry.isoformat(),
        opened_at=now,
        entry_spot=chain.spot,
        entry_iv=state.market.iv,
        rate=rate,
        dividend=dividend,
        exercise=exercise,
        legs=[
            PaperLeg(
                right=leg.right,
                side=leg.side,
                strike=leg.strike,
                contracts=leg.qty,
                entry_price=leg.premium,
            )
            for leg in basket
        ],
        forecast=Forecast(
            prob_profit=analytics.prob_profit,
            break_evens=list(analytics.break_evens),
            max_profit=dollars(analytics.max_profit, analytics.profit_unbounded),
            max_loss=dollars(analytics.max_loss, analytics.loss_unbounded),
        ),
        note=note.strip()[:300],
    )
    position = _with_valuation(position, chain, day)
    positions = list_for(username)
    positions.append(position)
    _store(username, positions)
    return position


# ---------------------------------------------------------------------------
# Valutazione
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LegMark:
    """Prezzo attuale di una gamba e da dove viene."""

    mark: float  # mid di mercato
    exit: float  # prezzo a cui la si chiuderebbe: denaro se long, lettera se short
    source: Literal["mercato", "modello", "intrinseco"]


def _intrinsic(leg: PaperLeg, spot: float) -> float:
    if leg.right == "call":
        return max(spot - leg.strike, 0.0)
    return max(leg.strike - spot, 0.0)


def mark_leg(position: PaperPosition, leg: PaperLeg, chain: Chain, today: date) -> LegMark:
    """Prezzo attuale di una gamba.

    - scaduta: valore intrinseco sul prezzo attuale del titolo;
    - quotata: mid di mercato, e per chiudere denaro (long) o lettera (short);
    - non quotata (strike sparito o senza prezzi): stima del modello con la
      volatilità ATM della scadenza.
    """
    expiry = position.expiry_date
    if expiry <= today:
        value = _intrinsic(leg, chain.spot)
        return LegMark(value, value, "intrinseco")
    quote: Quote | None = chain.quote(expiry, leg.right, leg.strike)  # type: ignore[arg-type]
    mid = quote.mid if quote is not None else None
    if quote is not None and mid is not None:
        if leg.side == "long":
            exit_price = quote.bid if quote.bid > 0 else mid
        else:
            exit_price = quote.ask if quote.ask > 0 else mid
        return LegMark(mid, exit_price, "mercato")
    iv = chain.atm_iv(expiry) or chain.iv30 or position.entry_iv
    spec = OptionSpec(
        spot=chain.spot,
        strike=leg.strike,
        days_to_expiry=float((expiry - today).days),
        risk_free_rate=position.rate,
        iv=iv,
        right=leg.right,  # type: ignore[arg-type]
        dividend_yield=position.dividend,
    )
    value = price_option(spec, position.exercise, "full")  # type: ignore[arg-type]
    return LegMark(value, value, "modello")


def _total(position: PaperPosition, prices: list[float]) -> float:
    return (
        sum(
            leg.sign * price * leg.contracts
            for leg, price in zip(position.legs, prices, strict=True)
        )
        * MULTIPLIER
    )


def _with_valuation(position: PaperPosition, chain: Chain, today: date) -> PaperPosition:
    marks = [mark_leg(position, leg, chain, today) for leg in position.legs]
    value = _total(position, [m.mark for m in marks])
    day = today.isoformat()
    snapshots = [s for s in position.snapshots if s.day != day]
    snapshots.append(Snapshot(day=day, spot=chain.spot, value=value))
    updated = replace(
        position,
        last_value=value,
        last_spot=chain.spot,
        last_iv=chain.atm_iv(position.expiry_date) if position.expiry_date > today else None,
        last_update=datetime.now(UTC).isoformat(timespec="seconds"),
        snapshots=sorted(snapshots, key=lambda s: s.day),
    )
    if position.expiry_date <= today:
        # Scaduta: si regola al valore intrinseco e si chiude da sola.
        return replace(
            updated,
            status="closed",
            closed_at=updated.last_update,
            exit_value=value,
            settled_at_expiry=True,
        )
    return updated


def refresh(username: str, chains: dict[str, Chain], today: date | None = None) -> int:
    """Aggiorna le posizioni aperte con le catene scaricate. Restituisce quante."""
    day = today or date.today()
    count = 0
    positions = list_for(username)
    for index, position in enumerate(positions):
        chain = chains.get(position.ticker)
        if position.status != "open" or chain is None:
            continue
        positions[index] = _with_valuation(position, chain, day)
        count += 1
    _store(username, positions)
    return count


def close_position(
    username: str, position_id: str, chain: Chain, today: date | None = None
) -> PaperPosition:
    """Chiude ai prezzi reali: le gambe comprate si vendono al denaro, le vendute
    si ricomprano alla lettera. È il costo vero dell'uscita."""
    day = today or date.today()
    position = next(p for p in list_for(username) if p.position_id == position_id)
    updated = _with_valuation(position, chain, day)
    if updated.status == "open":
        marks = [mark_leg(position, leg, chain, day) for leg in position.legs]
        updated = replace(
            updated,
            status="closed",
            closed_at=updated.last_update,
            exit_value=_total(position, [m.exit for m in marks]),
        )
    _replace(username, updated)
    return updated


def tickers_to_refresh(username: str) -> list[str]:
    return sorted({p.ticker for p in list_for(username) if p.status == "open"})


# ---------------------------------------------------------------------------
# Previsioni contro realtà
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Calibration:
    closed: int
    wins: int
    average_probability: float  # probabilità di profitto media prevista
    realized_pl: float

    @property
    def win_rate(self) -> float:
        return self.wins / self.closed if self.closed else 0.0


def calibration(positions: list[PaperPosition]) -> Calibration | None:
    """Quante posizioni chiuse sono finite in guadagno, contro quanto prevedeva il modello."""
    closed = [p for p in positions if p.status == "closed" and p.pl is not None]
    if not closed:
        return None
    return Calibration(
        closed=len(closed),
        wins=sum(1 for p in closed if (p.pl or 0.0) > 0),
        average_probability=statistics.mean(p.forecast.prob_profit for p in closed),
        realized_pl=sum(p.pl or 0.0 for p in closed),
    )
