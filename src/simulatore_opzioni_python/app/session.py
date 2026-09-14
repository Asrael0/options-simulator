"""Posizione per utente, condivisa fra le pagine.

--- COSA FA QUESTO FILE ---
Ricorda la posizione di ogni utente mentre naviga fra le pagine, e tiene i
contatori che la pagina di amministrazione mostra.

Il problema che risolve: con una pagina sola lo stato poteva vivere dentro la
funzione della pagina. Con più pagine no — navigando da «Posizione» a «Greche»
la funzione viene rieseguita da capo, e uno stato locale ripartirebbe dai
valori iniziali.

Le posizioni vivono in memoria e non sono persistenti: riavviando il server
ripartono dai valori di default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from nicegui import app

from .state import PositionState

_FALLBACK_KEY = "sconosciuto"


@dataclass(slots=True)
class SessionInfo:
    key: str
    position: PositionState
    username: str | None
    started_at: datetime
    last_seen: datetime
    page_views: int = 0


_SESSIONS: dict[str, SessionInfo] = {}


def _session_key() -> str:
    value = app.storage.browser.get("id")
    return value if isinstance(value, str) else _FALLBACK_KEY


def touch(username: str | None = None) -> SessionInfo:
    """Registra un accesso e restituisce la sessione corrente."""
    key = _session_key()
    now = datetime.now(UTC)
    info = _SESSIONS.get(key)
    if info is None:
        info = SessionInfo(
            key=key,
            position=PositionState(),
            username=username,
            started_at=now,
            last_seen=now,
        )
        _SESSIONS[key] = info
    info.last_seen = now
    info.page_views += 1
    if username is not None:
        info.username = username
    return info


def position() -> PositionState:
    """Posizione dell'utente corrente, creata al primo accesso."""
    return touch().position


def reset_position() -> None:
    """Riporta la posizione ai valori iniziali, conservando l'identità."""
    key = _session_key()
    existing = _SESSIONS.get(key)
    now = datetime.now(UTC)
    _SESSIONS[key] = SessionInfo(
        key=key,
        position=PositionState(),
        username=existing.username if existing is not None else None,
        started_at=now,
        last_seen=now,
    )


def all_sessions() -> list[SessionInfo]:
    """Tutte le sessioni note. Serve alla pagina di amministrazione."""
    return sorted(_SESSIONS.values(), key=lambda s: s.last_seen, reverse=True)


def session_count() -> int:
    return len(_SESSIONS)


@dataclass(slots=True)
class ServerStats:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    page_views: int = 0
    logins: int = 0
    failed_logins: int = 0
    registrations: int = 0


STATS = ServerStats()
