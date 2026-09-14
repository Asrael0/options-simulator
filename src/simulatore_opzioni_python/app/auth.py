"""Account, password e sessioni.

--- COSA FA QUESTO FILE ---
Tutto ciò che riguarda gli utenti: crearli, verificarne la password, ricordare
chi è collegato, controllare i permessi. È l'unico file che scrive su disco.

SICUREZZA — cosa è protetto e cosa no.

Le password non vengono MAI salvate in chiaro: si salva solo il risultato di
``pbkdf2_hmac`` con 600.000 iterazioni e un sale casuale diverso per ogni
utente. Il sale impedisce che due password uguali producano lo stesso hash, e
le iterazioni rendono costoso provare milioni di password su un file rubato.
Il confronto usa ``hmac.compare_digest``, che impiega sempre lo stesso tempo:
un confronto normale (``==``) esce al primo byte diverso, e da quanto ci mette
si può ricostruire l'hash un byte alla volta.

ATTENZIONE, e va detto chiaramente: l'account ``admin`` nasce con password
``admin``. Va bene per uno strumento didattico che gira su ``localhost``, dove
l'unico che può collegarsi sei tu. Non va bene in nessun altro contesto: se
mai esponessi questa applicazione su una rete raggiungibile da altri, cambia
quella password PRIMA di farlo. L'app lo ricorda anche a schermo finché la
password di default resta invariata.
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

DATA_DIR = Path.home() / ".simulatore-opzioni"
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
    """Trasforma password + sale nell'impronta da salvare."""
    return hashlib.pbkdf2_hmac(_ALGORITHM, password.encode(), salt, _ITERATIONS).hex()


def _now() -> str:
    """Istante attuale come testo, in UTC."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_users() -> dict[str, User]:
    """Legge il file degli utenti. Un file assente o rotto non è fatale."""
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
    """Riscrive il file degli utenti da zero."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {name: asdict(user) for name, user in users.items()}
    USERS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def ensure_default_admin() -> None:
    """Crea l'account amministratore se non esiste."""
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
    """Chiave con cui NiceGUI firma i cookie di sessione.

    Va generata una volta e conservata: se cambiasse a ogni avvio, tutte le
    sessioni verrebbero invalidate a ogni riavvio del server. Non è una
    password ed è specifica di questa installazione.
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
    """Restituisce l'utente se la password è corretta, altrimenti ``None``."""
    user = load_users().get(username)
    if user is None:
        _derive(password, secrets.token_bytes(_SALT_BYTES))
        return None
    candidate = _derive(password, bytes.fromhex(user.salt))
    return user if hmac.compare_digest(candidate, user.password_hash) else None


def register_user(username: str, password: str, confirm: str) -> str | None:
    """Crea un account. Restituisce un messaggio d'errore, o ``None`` se ok."""
    username = username.strip()
    if len(username) < MIN_USERNAME_LENGTH:
        return f"Il nome utente deve avere almeno {MIN_USERNAME_LENGTH} caratteri."
    if not username.replace("_", "").replace("-", "").isalnum():
        return "Il nome utente può contenere solo lettere, numeri, trattini e underscore."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"La password deve avere almeno {MIN_PASSWORD_LENGTH} caratteri."
    if password != confirm:
        return "Le due password non coincidono."

    users = load_users()
    if username in users:
        return "Questo nome utente è già in uso."

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
    """Cambia la password di un utente. Restituisce un errore o ``None``."""
    if verify_credentials(username, current) is None:
        return "La password attuale non è corretta."
    if len(new) < MIN_PASSWORD_LENGTH:
        return f"La nuova password deve avere almeno {MIN_PASSWORD_LENGTH} caratteri."
    if new != confirm:
        return "Le due password non coincidono."

    users = load_users()
    user = users.get(username)
    if user is None:
        return "Utente non trovato."

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
# Sessione del browser
# ---------------------------------------------------------------------------


def start_session(user: User) -> None:
    """``app.storage.user`` è un dizionario per scheda-utente, firmato."""
    app.storage.user.update({"username": user.username, "is_admin": user.is_admin, "since": _now()})


def end_session() -> None:
    app.storage.user.clear()


def current_username() -> str | None:
    value = app.storage.user.get("username")
    return value if isinstance(value, str) else None


def current_user() -> User | None:
    username = current_username()
    return load_users().get(username) if username else None


def is_admin() -> bool:
    """Il ruolo si rilegge dal file, non dalla sessione.

    Fidarsi del flag salvato in sessione significherebbe che una revoca dei
    privilegi non ha effetto finché l'utente non si riconnette.
    """
    user = current_user()
    return user is not None and user.is_admin


def require_login() -> bool:
    """Da chiamare all'inizio di ogni pagina protetta."""
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
