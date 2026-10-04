"""State of the «Real options» page and small formatting helpers."""

from __future__ import annotations

from datetime import date, datetime

from ....pricing import MertonFit, Right
from ... import session
from ...carry import (
    DEFAULT_RATE,
    Carry,
    ParityCheck,
)
from ...formatting import format_date, format_number, format_short_date
from ...i18n import tr
from ...market_data import (
    Chain,
)
from ...volatility import VolatilityReport

RANGES: dict[str, float | None] = {
    "±5%": 0.05,
    "±10%": 0.10,
    "±20%": 0.20,
    "±35%": 0.35,
    "Tutti": None,
}
DEFAULT_RANGE = "±10%"
CONTRACT_MULTIPLIER = 100

SIDE_CELLS = ["Denaro", "Lettera", "IV", "Δ", "OI"]


class MarketView:
    """Page state: the loaded chain and the control settings."""

    def __init__(self, info: session.SessionInfo) -> None:
        self.info = info
        self.chain: Chain | None = None
        self.loading = False
        self.range_key = DEFAULT_RANGE
        self.model_iv: float | None = None  # None = the expiry's ATM IV
        # Rate, dividend and style derived from the market; the «manual_» ones
        # are typed by hand in the comparison tab (None = use the derived ones).
        self.carry: Carry | None = None
        self.check: ParityCheck | None = None
        self.checking = False
        # «Volatility» tab: history and comparison with IV.
        self.vol: VolatilityReport | None = None
        self.vol_error: str | None = None
        self.vol_loading = False
        self.manual_rate: float | None = None
        self.manual_dividend: float | None = None
        self.manual_exercise: str | None = None
        self.pending: tuple[Right, float] | None = None
        # Merton calibration, valid only for the stock and expiry it was run on.
        self.merton: MertonFit | None = None
        self.merton_key: tuple[str, date] | None = None
        self.calibrating = False

    @property
    def rate(self) -> float:
        if self.manual_rate is not None:
            return self.manual_rate
        return self.carry.rate.rate if self.carry else DEFAULT_RATE

    def dividend(self, expiry: date) -> float:
        if self.manual_dividend is not None:
            return self.manual_dividend
        return self.carry.dividend(expiry) if self.carry else 0.0

    @property
    def exercise(self) -> str:
        if self.manual_exercise is not None:
            return self.manual_exercise
        return self.carry.exercise if self.carry else "american"

    def merton_for(self, expiry: date) -> MertonFit | None:
        """The Merton fit, if it belongs to the loaded stock and ``expiry``."""
        if self.chain is None or self.merton_key != (self.chain.ticker, expiry):
            return None
        return self.merton

    def reset_carry(self) -> None:
        self.manual_rate = self.manual_dividend = self.manual_exercise = None

    @property
    def expiry(self) -> date | None:
        if self.chain is None:
            return None
        chosen = self.info.market_expiry
        if chosen in self.chain.quotes:
            return chosen
        # First expiry at least a week out: dailies are noisy.
        later = [e for e in self.chain.expiries if (e - date.today()).days >= 7]
        return later[0] if later else self.chain.expiries[0]

    def visible_strikes(self) -> list[float]:
        if self.chain is None or self.expiry is None:
            return []
        strikes = self.chain.strikes(self.expiry)
        width = RANGES[self.range_key]
        if width is None:
            return strikes
        spot = self.chain.spot
        return [k for k in strikes if abs(k - spot) <= spot * width]


def expiry_label(expiry: date) -> str:
    days = (expiry - date.today()).days
    return tr("{date} · {days} gg", date=format_date(expiry), days=days)


def quoted_at(raw: str) -> str:
    """CBOE's ``2026-10-03 03:44:04`` becomes ``03/10 03:44`` (or ``3 Oct 03:44``)."""
    try:
        when = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return f"{format_short_date(when.date())} {when.strftime('%H:%M')}"
    except ValueError:
        return raw or "—"


def price_text(value: float | None) -> str:
    return "—" if value is None or value <= 0 else format_number(value, 2)
