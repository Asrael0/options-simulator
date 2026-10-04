"""Administration page: the state of everything.

One screen showing how long the server has been up, how many pages it served,
successful and failed logins, the pricing engine cache efficiency, library
versions, the user list and active sessions.

Visible only to administrator accounts. The check does not trust the flag stored
in the session: it re-reads the role from the users file on every visit,
otherwise revoking privileges would have no effect until logout.
"""

from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime

import numpy
from nicegui import __version__ as nicegui_version
from nicegui import ui

from ... import __version__ as app_version
from ...pricing import StockLeg, clear_price_cache, price_cache_info
from .. import auth, session
from ..formatting import format_number, format_percent, format_timestamp
from ..i18n import tr, trn
from ..layout import page_frame
from ..tickers import display_symbol
from ..widgets import CARD, DANGER, FAINT, MUTED, card_title


def _humanize(delta_seconds: float) -> str:
    """Turn a number of seconds into "2d 5h 13m"."""
    seconds = int(delta_seconds)
    days, seconds = divmod(seconds, 86_400)
    hours, seconds = divmod(seconds, 3_600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}{tr('g')} {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _kv_row(label: str, value: str) -> None:
    with ui.row().classes("w-full justify-between no-wrap gap-4 py-1 text-xs"):
        ui.label(tr(label)).classes(MUTED + " shrink-0")
        ui.label(value).classes("t-text2 text-right break-all")


@ui.page("/admin")
def admin_page() -> None:
    if not auth.require_admin():
        return

    with page_frame("/admin", subtitle=tr("Stato del server, utenti e sessioni")):
        content = ui.column().classes("w-full gap-4")

        def _flush_cache() -> None:
            clear_price_cache()
            ui.notify(tr("Cache svuotata"), type="positive")
            dashboard.refresh()

        @ui.refreshable
        def dashboard() -> None:
            now = datetime.now(UTC)
            users = auth.load_users()
            sessions = session.all_sessions()
            stats = session.STATS
            cache = price_cache_info()

            if any(u.is_admin and u.default_password for u in users.values()):
                ui.label(
                    tr(
                        "⚠ Un account amministratore usa ancora la password "
                        "predefinita «admin». Cambiala dalla pagina «Impostazioni» "
                        "prima di rendere raggiungibile questa applicazione da altri "
                        "computer."
                    )
                ).classes(DANGER)

            with ui.row().classes("w-full gap-4 items-start no-wrap max-lg:flex-wrap"):
                # ---------------------------------------------------------
                with ui.column().classes("gap-4 grow min-w-0"):
                    with ui.card().classes(CARD):
                        card_title(tr("Server"), "dns")
                        uptime = (now - stats.started_at).total_seconds()
                        _kv_row("Attivo da", _humanize(uptime))
                        _kv_row(
                            "Avviato il",
                            format_timestamp(stats.started_at.isoformat()),
                        )
                        _kv_row("Pagine servite", format_number(stats.page_views, 0))
                        _kv_row("Accessi riusciti", format_number(stats.logins, 0))
                        _kv_row(
                            "Accessi falliti",
                            format_number(stats.failed_logins, 0),
                        )
                        _kv_row("Registrazioni", format_number(stats.registrations, 0))
                        ui.label(
                            tr(
                                "I contatori si azzerano a ogni riavvio del server: "
                                "vivono in memoria, non su disco."
                            )
                        ).classes(FAINT)

                    with ui.card().classes(CARD):
                        card_title(tr("Cache del motore di pricing"), "memory")
                        total = cache["hits"] + cache["misses"]
                        rate = cache["hits"] / total if total else 0.0
                        _kv_row("Richieste servite dalla cache", format_number(cache["hits"], 0))
                        _kv_row("Calcoli eseguiti", format_number(cache["misses"], 0))
                        _kv_row("Tasso di riuso", format_percent(rate, 1))
                        _kv_row(
                            "Voci in cache",
                            f"{format_number(cache['size'], 0)} / "
                            f"{format_number(cache['maxsize'], 0)}",
                        )
                        ui.label(
                            tr(
                                "Riguarda solo l'albero binomiale: le europee usano "
                                "una formula chiusa e non hanno bisogno di cache."
                            )
                        ).classes(FAINT)
                        ui.button(tr("Svuota la cache"), on_click=_flush_cache).props(
                            "outline dense no-caps color=warning"
                        ).classes("text-xs mt-1")

                    with ui.card().classes(CARD):
                        card_title(tr("Ambiente"), "terminal")
                        _kv_row("Versione applicazione", app_version)
                        _kv_row("Python", sys.version.split()[0])
                        _kv_row("NumPy", numpy.__version__)
                        _kv_row("NiceGUI", nicegui_version)
                        _kv_row("Sistema", f"{platform.system()} {platform.release()}")
                        _kv_row("File degli utenti", str(auth.USERS_FILE))

                # ---------------------------------------------------------
                with ui.column().classes("gap-4 grow min-w-0"):
                    with ui.card().classes(CARD):
                        card_title(tr("Utenti registrati ({len})", len=len(users)), "group")
                        with ui.row().classes("w-full gap-2 no-wrap sim-thead px-1"):
                            ui.label(tr("Nome utente")).classes("grow")
                            ui.label(tr("Ruolo")).classes("w-28")
                            ui.label(tr("Creato")).classes("w-40 text-right")
                        for user in sorted(
                            users.values(), key=lambda u: (not u.is_admin, u.username)
                        ):
                            with ui.row().classes(
                                "w-full gap-2 no-wrap text-xs py-1 sim-divider items-center"
                            ):
                                ui.label(user.username).classes("grow t-text2")
                                with ui.row().classes("w-28 gap-1 no-wrap items-center"):
                                    ui.label(
                                        tr("amministratore") if user.is_admin else tr("utente")
                                    ).classes(
                                        "text-[10px] "
                                        + ("t-accent font-bold" if user.is_admin else "t-muted")
                                    )
                                    if user.default_password:
                                        ui.icon("warning", size="14px").classes("t-loss").tooltip(
                                            tr("Password predefinita mai cambiata")
                                        )
                                ui.label(format_timestamp(user.created_at)).classes(
                                    "w-40 text-right t-faint"
                                )

                    with ui.card().classes(CARD):
                        card_title(tr("Sessioni attive ({len})", len=len(sessions)), "devices")
                        if not sessions:
                            ui.label(tr("Nessuna sessione registrata.")).classes(FAINT)
                        for info in sessions:
                            position = info.position
                            stock_legs = sum(
                                1 for leg in position.legs if isinstance(leg, StockLeg)
                            )
                            idle = (now - info.last_seen).total_seconds()
                            with ui.column().classes("w-full gap-0 py-2 sim-divider"):
                                with ui.row().classes("w-full justify-between no-wrap"):
                                    ui.label(info.username or tr("non autenticato")).classes(
                                        "text-xs font-semibold t-text2"
                                    )
                                    ui.label(
                                        tr("inattivo da {humanize}", humanize=_humanize(idle))
                                    ).classes("text-[11px] t-faint")
                                style = (
                                    tr("europee")
                                    if position.exercise == "european"
                                    else tr("americane")
                                )
                                ui.label(
                                    tr(
                                        "{symbol} · {legs} ({stock_legs} azionarie) · {style} · "
                                        "spot {spot} · IV {iv} · {days_to_expiry} gg",
                                        symbol=display_symbol(position.ticker),
                                        legs=trn("{n} gamba", "{n} gambe", len(position.legs)),
                                        stock_legs=stock_legs,
                                        style=style,
                                        spot=format_number(position.market.spot, 2),
                                        iv=format_percent(position.market.iv, 1),
                                        days_to_expiry=format_number(
                                            position.market.days_to_expiry, 0
                                        ),
                                    )
                                ).classes(FAINT)
                                ui.label(
                                    tr(
                                        "sessione {key}… · {page_views} pagine viste",
                                        key=info.key[:12],
                                        page_views=info.page_views,
                                    )
                                ).classes("text-[10px] t-faint opacity-70")

            ui.button(tr("Aggiorna"), icon="refresh", on_click=dashboard.refresh).props(
                "unelevated dense no-caps color=primary"
            ).classes("text-xs")

        with content:
            dashboard()
