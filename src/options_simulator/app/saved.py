"""Posizioni salvate da ogni utente.

--- COSA FA QUESTO FILE ---
Permette di dare un nome alla posizione che si sta studiando e ritrovarla in
seguito, anche dopo aver spento il simulatore. Tutto finisce in un file JSON
accanto a quello degli utenti: ``~/.options-simulator/posizioni.json``.

Il file contiene, per ogni utente, un elenco di posizioni. Ognuna conserva
TUTTO ciò che serve a ricostruirla: mercato, premi d'ingresso, gambe (con gli
eventuali premi imposti a mano), dimensionamento e scenario.
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
    return auth.DATA_DIR / "posizioni.json"


# ---------------------------------------------------------------------------
# Da stato a dizionario e ritorno
# ---------------------------------------------------------------------------


def to_dict(state: PositionState) -> dict[str, Any]:
    """Fotografia della posizione, fatta solo di numeri e testi."""
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
    """Ricostruisce una posizione. Solleva ``ValueError`` se i dati sono rotti."""
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
            raise ValueError("posizione senza gambe")
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
        raise ValueError(f"posizione salvata non leggibile: {error}") from error


# ---------------------------------------------------------------------------
# Lettura e scrittura del file
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
    """Posizioni dell'utente, dalla più recente."""
    items: list[SavedPosition] = []
    for raw in _load_all().get(username, []):
        try:
            items.append(SavedPosition(**raw))
        except TypeError:
            continue
    return sorted(items, key=lambda p: p.saved_at, reverse=True)


def save(username: str, name: str, state: PositionState) -> str | None:
    """Salva la posizione. Restituisce un messaggio d'errore, o ``None``.

    Un nome già usato sovrascrive la posizione con quel nome: è il
    comportamento che ci si aspetta da «Salva» dopo averla modificata.
    """
    name = name.strip()
    if not name:
        return "Dai un nome alla posizione."
    if len(name) > MAX_NAME_LENGTH:
        return f"Il nome può avere al massimo {MAX_NAME_LENGTH} caratteri."
    payload = _load_all()
    mine = [p for p in payload.get(username, []) if p.get("name") != name]
    if len(mine) >= MAX_PER_USER:
        return f"Hai già {MAX_PER_USER} posizioni salvate: eliminane qualcuna."
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
# File da scambiare: esporta e importa
# ---------------------------------------------------------------------------

FILE_FORMAT = "options-simulator"
# Etichetta dei file esportati prima del passaggio ai nomi in inglese: si leggono ancora.
ACCEPTED_FORMATS = {FILE_FORMAT, "simulatore-opzioni"}
FILE_VERSION = 1


def export_bytes(name: str, state: PositionState) -> bytes:
    """Posizione come file JSON da scaricare e condividere."""
    payload = {
        "formato": FILE_FORMAT,
        "versione": FILE_VERSION,
        "nome": name,
        "esportata_il": datetime.now(UTC).isoformat(timespec="seconds"),
        "posizione": to_dict(state),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def import_bytes(content: bytes) -> tuple[str, PositionState]:
    """Legge un file esportato. Solleva ``ValueError`` con un messaggio leggibile."""
    try:
        payload: Any = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Il file non è un JSON valido.") from error
    if not isinstance(payload, dict) or payload.get("formato") not in ACCEPTED_FORMATS:
        raise ValueError("Il file non è una posizione esportata dal simulatore.")
    if payload.get("versione", 0) > FILE_VERSION:
        raise ValueError("Il file viene da una versione più recente del simulatore.")
    state = from_dict(payload.get("posizione", {}))
    name = str(payload.get("nome") or state.ticker)[:MAX_NAME_LENGTH]
    return name, state
