"""Virtual portfolio: make-believe positions opened at real prices.

It closes the learning loop. The simulator says what *should* happen; here a
position is opened at today's real prices, and coming back over the following
days shows what really happened.

For each position it keeps:
  - WHAT was done: the legs, at the prices really paid or received (buyers pay
    the ask, sellers receive the bid);
  - WHAT THE MODEL PREDICTED at that moment: probability of profit, break-evens,
    maximum gain and loss;
  - HOW IT WENT: one point per day with the stock price and position value,
    until it is closed.

Everything is stored in ``~/.options-simulator/portfolio.json``, per user.

REAL DOLLAR VALUES. Unlike the simulator, which works "per share", every figure
here is already multiplied by the contract multiplier (100 shares) and by the
number of contracts: it is what the account would show.

LIMITS, stated plainly:
  - no commissions and no margin;
  - no early exercise or assignment before expiry;
  - an expired position is settled at intrinsic value using the stock price on
    the day it is refreshed, which can be after expiry: an approximation,
    flagged on screen.
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
    entry_price: float  # per share, as really paid or received

    @property
    def sign(self) -> float:
        return 1.0 if self.side == "long" else -1.0


@dataclass(frozen=True, slots=True)
class Snapshot:
    day: str  # ISO date, one per day
    spot: float
    value: float  # position value in $ (marked at mid)


@dataclass(frozen=True, slots=True)
class Forecast:
    """The model's forecast when the position was opened (in real $)."""

    prob_profit: float
    break_evens: list[float]
    max_profit: float | None  # None = unlimited
    max_loss: float | None


@dataclass(frozen=True, slots=True)
class PaperPosition:
    position_id: str
    ticker: str  # internal spelling (``_SPX``)
    name: str
    expiry: str  # ISO
    opened_at: str  # ISO timestamp
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

    # -- derived values ----------------------------------------------------

    @property
    def expiry_date(self) -> date:
        return date.fromisoformat(self.expiry)

    @property
    def entry_cost(self) -> float:
        """$ paid (positive) or received (negative) when opening."""
        return sum(leg.sign * leg.entry_price * leg.contracts for leg in self.legs) * MULTIPLIER

    @property
    def current_value(self) -> float | None:
        return self.exit_value if self.status == "closed" else self.last_value

    @property
    def pl(self) -> float | None:
        """Gain or loss in $: current (or closing) value minus cost."""
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
        """Legs summary, e.g. «Long 1 call 335 · Short 1 call 345»."""
        return " · ".join(
            f"{leg.side.title()} {leg.contracts:g} {leg.right} {leg.strike:g}" for leg in self.legs
        )


# ---------------------------------------------------------------------------
# Reading and writing
# ---------------------------------------------------------------------------


def _file() -> Path:
    return auth.DATA_DIR / "portfolio.json"


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
    """The user's positions: open ones first, then closed, newest first."""
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
# Opening
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
    """Record the position at the basket prices, with the model's forecast."""
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
# Valuation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LegMark:
    """A leg's current price and where it comes from."""

    mark: float  # market mid
    exit: float  # price it would close at: bid if long, ask if short
    source: Literal["market", "model", "intrinsic"]


def _intrinsic(leg: PaperLeg, spot: float) -> float:
    if leg.right == "call":
        return max(spot - leg.strike, 0.0)
    return max(leg.strike - spot, 0.0)


def mark_leg(position: PaperPosition, leg: PaperLeg, chain: Chain, today: date) -> LegMark:
    """Current price of a leg.

    - expired: intrinsic value at the current stock price;
    - quoted: market mid, and bid (long) or ask (short) to close;
    - not quoted (strike gone or without prices): model estimate using the
      expiry's ATM volatility.
    """
    expiry = position.expiry_date
    if expiry <= today:
        value = _intrinsic(leg, chain.spot)
        return LegMark(value, value, "intrinsic")
    quote: Quote | None = chain.quote(expiry, leg.right, leg.strike)  # type: ignore[arg-type]
    mid = quote.mid if quote is not None else None
    if quote is not None and mid is not None:
        if leg.side == "long":
            exit_price = quote.bid if quote.bid > 0 else mid
        else:
            exit_price = quote.ask if quote.ask > 0 else mid
        return LegMark(mid, exit_price, "market")
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
    return LegMark(value, value, "model")


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
        # Expired: settle at intrinsic value and close automatically.
        return replace(
            updated,
            status="closed",
            closed_at=updated.last_update,
            exit_value=value,
            settled_at_expiry=True,
        )
    return updated


def refresh(username: str, chains: dict[str, Chain], today: date | None = None) -> int:
    """Refresh the open positions with the downloaded chains. Return how many."""
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
    """Close at real prices: bought legs are sold at the bid, sold legs are
    bought back at the ask. It is the true cost of exiting."""
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
# Forecasts against reality
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Calibration:
    closed: int
    wins: int
    average_probability: float  # average predicted probability of profit
    realized_pl: float

    @property
    def win_rate(self) -> float:
        return self.wins / self.closed if self.closed else 0.0


def calibration(positions: list[PaperPosition]) -> Calibration | None:
    """How many closed positions ended in profit, against what the model predicted."""
    closed = [p for p in positions if p.status == "closed" and p.pl is not None]
    if not closed:
        return None
    return Calibration(
        closed=len(closed),
        wins=sum(1 for p in closed if (p.pl or 0.0) > 0),
        average_probability=statistics.mean(p.forecast.prob_profit for p in closed),
        realized_pl=sum(p.pl or 0.0 for p in closed),
    )
