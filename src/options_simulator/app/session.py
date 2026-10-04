"""Per-user position, shared across pages.

Remembers each user's position while they move between pages, and keeps the
counters shown on the administration page.

The problem it solves: with a single page the state could live inside the page
function. With several pages it cannot — going from the «Guide» back to the
simulator re-runs the page function from scratch, and local state would reset.

Positions live in memory and are not persistent: restarting the server resets
them to the defaults (saved positions are on disk, see ``saved.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from nicegui import app

from .state import PositionState

if TYPE_CHECKING:
    from .market_data import BasketLeg

_FALLBACK_KEY = "unknown"


@dataclass(slots=True)
class SessionInfo:
    key: str
    position: PositionState
    username: str | None
    started_at: datetime
    last_seen: datetime
    page_views: int = 0
    # «Real options» page: loaded stock, chosen expiry and picked options, so
    # everything is still there when coming back to the page.
    market_ticker: str = ""
    market_expiry: date | None = None
    basket: list[BasketLeg] = field(default_factory=list)


_SESSIONS: dict[str, SessionInfo] = {}


def _session_key() -> str:
    value = app.storage.browser.get("id")
    return value if isinstance(value, str) else _FALLBACK_KEY


def touch(username: str | None = None) -> SessionInfo:
    """Record a visit and return the current session."""
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
    """The current user's position, created on the first visit."""
    return touch().position


def replace_position(state: PositionState) -> None:
    """Replace the current position, for example with a saved one."""
    info = _SESSIONS.get(_session_key())
    if info is None:
        info = touch()
    info.position = state


def all_sessions() -> list[SessionInfo]:
    """Every known session, for the administration page."""
    return sorted(_SESSIONS.values(), key=lambda s: s.last_seen, reverse=True)


@dataclass(slots=True)
class ServerStats:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    page_views: int = 0
    logins: int = 0
    failed_logins: int = 0
    registrations: int = 0


STATS = ServerStats()
