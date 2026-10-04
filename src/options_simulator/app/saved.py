"""Positions saved by each user.

Lets the user name the position being studied and find it again later, even
after shutting the simulator down. Everything goes into a JSON file next to the
users file: ``~/.options-simulator/positions.json``.

For each user the file holds a list of positions. Each one keeps EVERYTHING
needed to rebuild it: market, entry premiums, legs (with any manual premiums),
sizing and scenario.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..pricing import (
    ManualPremium,
    MarketParams,
    OptionLeg,
    Sizing,
    StockLeg,
    TheoreticalPremium,
)
from . import auth
from .i18n import tr
from .state import PositionState
from .strategies import new_leg_id
from .tickers import display_symbol

MAX_PER_USER = 50
MAX_NAME_LENGTH = 60


@dataclass(frozen=True, slots=True)
class SavedPosition:
    position_id: str
    name: str
    saved_at: str
    data: dict[str, Any]

    @property
    def ticker(self) -> str:
        return str(self.data.get("ticker", ""))

    @property
    def leg_count(self) -> int:
        return len(self.data.get("legs", []))

    @property
    def exercise(self) -> str:
        return str(self.data.get("exercise", "european"))


def _file() -> Path:
    return auth.DATA_DIR / "positions.json"


# ---------------------------------------------------------------------------
# From state to dictionary and back
# ---------------------------------------------------------------------------


def to_dict(state: PositionState) -> dict[str, Any]:
    """Snapshot of the position, made only of numbers and text."""
    legs: list[dict[str, Any]] = []
    for leg in state.legs:
        if isinstance(leg, StockLeg):
            legs.append(
                {"type": "stock", "side": leg.side, "qty": leg.qty, "entry_price": leg.entry_price}
            )
        else:
            legs.append(
                {
                    "type": leg.right,
                    "side": leg.side,
                    "qty": leg.qty,
                    "strike": leg.strike,
                    "premium": leg.premium.value
                    if isinstance(leg.premium, ManualPremium)
                    else None,
                    "iv_override": leg.iv_override,
                }
            )
    return {
        "ticker": state.ticker,
        "name": state.name,
        "market": asdict(state.market),
        "entry_market": asdict(state.entry_market),
        "pin_premiums": state.pin_premiums,
        "exercise": state.exercise,
        "compare_exercise": state.compare_exercise,
        "legs": legs,
        "strategy_key": state.strategy_key,
        "target": state.target,
        "iv_sim": state.iv_sim,
        "sizing": asdict(state.sizing),
        "currency": state.currency,
    }


def from_dict(data: dict[str, Any]) -> PositionState:
    """Rebuild a position. Raise ``ValueError`` if the data is broken."""
    try:
        legs: list[OptionLeg | StockLeg] = []
        for raw in data["legs"]:
            if raw["type"] == "stock":
                legs.append(
                    StockLeg(
                        leg_id=new_leg_id(),
                        side=raw["side"],
                        qty=float(raw["qty"]),
                        entry_price=float(raw["entry_price"]),
                    )
                )
                continue
            premium = raw.get("premium")
            legs.append(
                OptionLeg(
                    leg_id=new_leg_id(),
                    side=raw["side"],
                    qty=float(raw["qty"]),
                    right=raw["type"],
                    strike=float(raw["strike"]),
                    premium=TheoreticalPremium()
                    if premium is None
                    else ManualPremium(float(premium)),
                    iv_override=raw.get("iv_override"),
                )
            )
        if not legs:
            raise ValueError("position without legs")
        return PositionState(
            ticker=display_symbol(str(data["ticker"])),
            name=str(data["name"]),
            market=MarketParams(**data["market"]),
            entry_market=MarketParams(**data["entry_market"]),
            pin_premiums=bool(data["pin_premiums"]),
            exercise=data["exercise"],
            compare_exercise=bool(data.get("compare_exercise", False)),
            legs=legs,
            strategy_key=str(data.get("strategy_key", "single")),
            target=float(data["target"]),
            iv_sim=float(data["iv_sim"]),
            sizing=Sizing(**data["sizing"]),
            currency=str(data.get("currency", "$")),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"unreadable saved position: {error}") from error


# ---------------------------------------------------------------------------
# Reading and writing the file
# ---------------------------------------------------------------------------


def _load_all() -> dict[str, list[dict[str, Any]]]:
    try:
        raw: Any = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_all(payload: dict[str, list[dict[str, Any]]]) -> None:
    auth.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_for(username: str) -> list[SavedPosition]:
    """The user's positions, newest first."""
    items: list[SavedPosition] = []
    for raw in _load_all().get(username, []):
        try:
            items.append(SavedPosition(**raw))
        except TypeError:
            continue
    return sorted(items, key=lambda p: p.saved_at, reverse=True)


def save(username: str, name: str, state: PositionState) -> str | None:
    """Save the position. Return an error message, or ``None``.

    A name already in use overwrites the position with that name: it is what
    «Save» is expected to do after editing it.
    """
    name = name.strip()
    if not name:
        return tr("Dai un nome alla posizione.")
    if len(name) > MAX_NAME_LENGTH:
        return tr("Il nome può avere al massimo {n} caratteri.", n=MAX_NAME_LENGTH)
    payload = _load_all()
    mine = [p for p in payload.get(username, []) if p.get("name") != name]
    if len(mine) >= MAX_PER_USER:
        return tr("Hai già {n} posizioni salvate: eliminane qualcuna.", n=MAX_PER_USER)
    saved = SavedPosition(
        position_id=secrets.token_hex(6),
        name=name,
        saved_at=datetime.now(UTC).isoformat(timespec="seconds"),
        data=to_dict(state),
    )
    mine.append(asdict(saved))
    payload[username] = mine
    _save_all(payload)
    return None


def get(username: str, position_id: str) -> SavedPosition | None:
    return next((p for p in list_for(username) if p.position_id == position_id), None)


def delete(username: str, position_id: str) -> None:
    payload = _load_all()
    payload[username] = [
        p for p in payload.get(username, []) if p.get("position_id") != position_id
    ]
    _save_all(payload)


# ---------------------------------------------------------------------------
# Shareable files: export and import
# ---------------------------------------------------------------------------

FILE_FORMAT = "options-simulator"
# Label of files exported before the switch to English names: still readable.
ACCEPTED_FORMATS = {FILE_FORMAT, "simulatore-opzioni"}
FILE_VERSION = 1
# Older files used Italian keys; they are still read.
_LEGACY_KEYS = {
    "format": "formato",
    "version": "versione",
    "name": "nome",
    "position": "posizione",
}


def _field(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in payload:
        return payload[key]
    return payload.get(_LEGACY_KEYS[key], default)


def export_bytes(name: str, state: PositionState) -> bytes:
    """The position as a JSON file to download and share."""
    payload = {
        "format": FILE_FORMAT,
        "version": FILE_VERSION,
        "name": name,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "position": to_dict(state),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def import_bytes(content: bytes) -> tuple[str, PositionState]:
    """Read an exported file. Raise ``ValueError`` with a readable message."""
    try:
        payload: Any = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(tr("Il file non è un JSON valido.")) from error
    if not isinstance(payload, dict) or _field(payload, "format") not in ACCEPTED_FORMATS:
        raise ValueError(tr("Il file non è una posizione esportata dal simulatore."))
    if _field(payload, "version", 0) > FILE_VERSION:
        raise ValueError(tr("Il file viene da una versione più recente del simulatore."))
    state = from_dict(_field(payload, "position", {}))
    name = str(_field(payload, "name") or state.ticker)[:MAX_NAME_LENGTH]
    return name, state
