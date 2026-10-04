"""Accounts, passwords and sessions.

Everything about users lives here: creating them, checking their password,
remembering who is logged in and checking permissions.

SECURITY — what is protected and what is not.

Passwords are NEVER stored in plain text: only the result of ``pbkdf2_hmac``
with 600,000 iterations and a different random salt per user is saved. The salt
stops two equal passwords from producing the same hash, and the iterations make
trying millions of passwords against a stolen file expensive. The comparison
uses ``hmac.compare_digest``, which always takes the same time: a plain ``==``
stops at the first different byte, and its timing would let an attacker rebuild
the hash one byte at a time.

Be aware: the ``admin`` account starts with the password ``admin``. That is fine
for an application running on ``localhost``, where the only person who can
connect is you. It is not fine anywhere else: before exposing this application
on a network reachable by others, change that password. The app keeps reminding
you on screen while the default password is in use.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nicegui import app, ui

from .i18n import tr

DATA_DIR = Path.home() / ".options-simulator"
# Folder and file names used before the project switched to English names.
LEGACY_DATA_DIR = Path.home() / ".simulatore-opzioni"
LEGACY_FILE_NAMES = {
    "posizioni.json": "positions.json",
    "portafoglio.json": "portfolio.json",
    "tasso.json": "rate.json",
}
USERS_FILE = DATA_DIR / "users.json"

_ALGORITHM = "sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 16

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"

MIN_PASSWORD_LENGTH = 4
MIN_USERNAME_LENGTH = 3


@dataclass(frozen=True, slots=True)
class User:
    username: str
    salt: str
    password_hash: str
    is_admin: bool
    created_at: str
    default_password: bool = False


def _derive(password: str, salt: bytes) -> str:
    """Turn password + salt into the fingerprint that gets stored."""
    return hashlib.pbkdf2_hmac(_ALGORITHM, password.encode(), salt, _ITERATIONS).hex()


def _now() -> str:
    """Current instant as text, in UTC."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_users() -> dict[str, User]:
    """Read the users file. A missing or broken file is not fatal."""
    try:
        raw: Any = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    users: dict[str, User] = {}
    for username, data in raw.items():
        try:
            users[username] = User(**data)
        except TypeError:
            continue
    return users


def save_users(users: dict[str, User]) -> None:
    """Rewrite the users file from scratch."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {name: asdict(user) for name, user in users.items()}
    USERS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def migrate_legacy_data_dir() -> None:
    """Move data written by older versions to the current names, once.

    Nothing is ever overwritten: a folder or file is renamed only when the new
    one does not exist yet, so from the second start on this does nothing.
    """
    if LEGACY_DATA_DIR.is_dir() and not DATA_DIR.exists():
        LEGACY_DATA_DIR.rename(DATA_DIR)
    for old, new in LEGACY_FILE_NAMES.items():
        if (DATA_DIR / old).is_file() and not (DATA_DIR / new).exists():
            (DATA_DIR / old).rename(DATA_DIR / new)


def ensure_default_admin() -> None:
    """Create the administrator account if there is none."""
    users = load_users()
    if any(u.is_admin for u in users.values()):
        return
    salt = secrets.token_bytes(_SALT_BYTES)
    users[DEFAULT_ADMIN_USERNAME] = User(
        username=DEFAULT_ADMIN_USERNAME,
        salt=salt.hex(),
        password_hash=_derive(DEFAULT_ADMIN_PASSWORD, salt),
        is_admin=True,
        created_at=_now(),
        default_password=True,
    )
    save_users(users)


def storage_secret() -> str:
    """Key NiceGUI uses to sign the session cookies.

    It is generated once and kept: if it changed at every start, every session
    would be invalidated whenever the server restarts. It is not a password and
    it is specific to this installation.
    """
    secret_file = DATA_DIR / "storage_secret.txt"
    try:
        existing = secret_file.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    except OSError:
        pass
    secret = secrets.token_urlsafe(32)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


def verify_credentials(username: str, password: str) -> User | None:
    """Return the user if the password is right, otherwise ``None``."""
    user = load_users().get(username)
    if user is None:
        # Same work as a real check, so timing does not reveal which usernames exist.
        _derive(password, secrets.token_bytes(_SALT_BYTES))
        return None
    candidate = _derive(password, bytes.fromhex(user.salt))
    return user if hmac.compare_digest(candidate, user.password_hash) else None


def register_user(username: str, password: str, confirm: str) -> str | None:
    """Create an account. Return an error message, or ``None`` on success."""
    username = username.strip()
    if len(username) < MIN_USERNAME_LENGTH:
        return tr("Il nome utente deve avere almeno {n} caratteri.", n=MIN_USERNAME_LENGTH)
    if not username.replace("_", "").replace("-", "").isalnum():
        return tr("Il nome utente può contenere solo lettere, numeri, trattini e underscore.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return tr("La password deve avere almeno {n} caratteri.", n=MIN_PASSWORD_LENGTH)
    if password != confirm:
        return tr("Le due password non coincidono.")

    users = load_users()
    if username in users:
        return tr("Questo nome utente è già in uso.")

    salt = secrets.token_bytes(_SALT_BYTES)
    users[username] = User(
        username=username,
        salt=salt.hex(),
        password_hash=_derive(password, salt),
        is_admin=False,
        created_at=_now(),
        default_password=False,
    )
    save_users(users)
    return None


def change_password(username: str, current: str, new: str, confirm: str) -> str | None:
    """Change a user's password. Return an error message, or ``None``."""
    if verify_credentials(username, current) is None:
        return tr("La password attuale non è corretta.")
    if len(new) < MIN_PASSWORD_LENGTH:
        return tr("La nuova password deve avere almeno {n} caratteri.", n=MIN_PASSWORD_LENGTH)
    if new != confirm:
        return tr("Le due password non coincidono.")

    users = load_users()
    user = users.get(username)
    if user is None:
        return tr("Utente non trovato.")

    salt = secrets.token_bytes(_SALT_BYTES)
    users[username] = User(
        username=user.username,
        salt=salt.hex(),
        password_hash=_derive(new, salt),
        is_admin=user.is_admin,
        created_at=user.created_at,
        default_password=False,
    )
    save_users(users)
    return None


# ---------------------------------------------------------------------------
# Browser session
# ---------------------------------------------------------------------------

_SESSION_KEYS = ("username", "is_admin", "since")


def start_session(user: User) -> None:
    """``app.storage.user`` is a signed dictionary, one per browser."""
    username, admin, since = _SESSION_KEYS
    app.storage.user.update({username: user.username, admin: user.is_admin, since: _now()})


def end_session() -> None:
    """Log out. Language, theme and colour stay: they belong to the browser."""
    for key in _SESSION_KEYS:
        app.storage.user.pop(key, None)


def current_username() -> str | None:
    value = app.storage.user.get("username")
    return value if isinstance(value, str) else None


def current_user() -> User | None:
    username = current_username()
    return load_users().get(username) if username else None


def is_admin() -> bool:
    """The role is read again from the file, not from the session.

    Trusting the flag stored in the session would mean that revoking privileges
    has no effect until the user logs in again.
    """
    user = current_user()
    return user is not None and user.is_admin


def require_login() -> bool:
    """Call at the top of every protected page."""
    if current_username() is None:
        ui.navigate.to("/login")
        return False
    return True


def require_admin() -> bool:
    if not require_login():
        return False
    if not is_admin():
        ui.navigate.to("/")
        return False
    return True
