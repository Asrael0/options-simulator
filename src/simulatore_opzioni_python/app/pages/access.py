"""Pagine di accesso, registrazione e cambio password.

--- COSA FA QUESTO FILE ---
Tre pagine: `/login`, `/registrati`, `/account`. Le prime due sono accessibili
senza essere collegati (altrimenti non ci si potrebbe mai collegare); la terza
richiede l'accesso.
"""

from __future__ import annotations

from nicegui import ui

from .. import auth, saved, session
from ..formatting import format_timestamp
from ..layout import centered_card, page_frame
from ..widgets import CARD, DANGER, FAINT, MUTED, card_title


@ui.page("/login")
def login_page() -> None:
    with centered_card("Accedi", "Serve un account per usare il simulatore."):
        username = ui.input("Nome utente").classes("w-full").props("dense outlined autofocus")
        password = (
            ui.input("Password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        error = ui.label("").classes("text-xs t-loss")

        def submit() -> None:
            user = auth.verify_credentials(username.value or "", password.value or "")
            if user is None:
                session.STATS.failed_logins += 1
                error.set_text("Nome utente o password non corretti.")
                return
            auth.start_session(user)
            session.STATS.logins += 1
            session.touch(user.username)
            ui.navigate.to("/")

        password.on("keydown.enter", submit)
        username.on("keydown.enter", submit)

        ui.button("Accedi", on_click=submit).props("unelevated no-caps").classes("w-full py-2 mt-1")
        with ui.row().classes("w-full justify-center gap-1 items-center"):
            ui.label("Non hai un account?").classes(MUTED)
            ui.button("Registrati", on_click=lambda: ui.navigate.to("/registrati")).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

        ui.separator()
        ui.label(
            "Primo avvio: esiste già un account amministratore con nome utente "
            "«admin» e password «admin». Cambiala dalla pagina Amministrazione."
        ).classes(FAINT)


@ui.page("/registrati")
def register_page() -> None:
    with centered_card("Crea un account"):
        username = ui.input("Nome utente").classes("w-full").props("dense outlined autofocus")
        password = (
            ui.input("Password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        confirm = (
            ui.input("Ripeti la password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        error = ui.label("").classes("text-xs t-loss")

        def submit() -> None:
            problem = auth.register_user(
                username.value or "", password.value or "", confirm.value or ""
            )
            if problem is not None:
                error.set_text(problem)
                return
            session.STATS.registrations += 1
            ui.notify("Account creato: ora puoi accedere", type="positive")
            ui.navigate.to("/login")

        confirm.on("keydown.enter", submit)

        ui.button("Crea account", on_click=submit).props("unelevated no-caps").classes(
            "w-full py-2 mt-1"
        )
        with ui.row().classes("w-full justify-center gap-1 items-center"):
            ui.label("Hai già un account?").classes(MUTED)
            ui.button("Accedi", on_click=lambda: ui.navigate.to("/login")).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

        ui.separator()
        ui.label(
            "Le password non vengono mai salvate in chiaro: il file contiene solo "
            "un hash pbkdf2 con 600.000 iterazioni e un sale casuale diverso per "
            "ogni utente."
        ).classes(FAINT)


@ui.page("/account")
def account_page() -> None:
    if not auth.require_login():
        return
    user = auth.current_user()
    if user is None:
        ui.navigate.to("/login")
        return

    with (
        page_frame(
            "/account", subtitle="Le tue posizioni salvate, la password e i dati dell'accesso"
        ),
        ui.row().classes("w-full gap-5 items-start no-wrap max-lg:flex-wrap"),
    ):
        with ui.column().classes("gap-5 grow min-w-0 w-full"):
            _saved_positions(user.username)

        with ui.column().classes("gap-5 w-full lg:w-[420px] shrink-0"):
            _password_card(user)
            with ui.card().classes(CARD):
                card_title("Dati dell'account", "badge")
                for label, value in [
                    ("Nome utente", user.username),
                    ("Ruolo", "amministratore" if user.is_admin else "utente"),
                    ("Creato il", format_timestamp(user.created_at)),
                ]:
                    with ui.row().classes("w-full justify-between text-sm py-2 sim-divider"):
                        ui.label(label).classes(MUTED)
                        ui.label(value).classes("t-text2")


def _saved_positions(username: str) -> None:
    """Elenco delle posizioni salvate, con apri ed elimina."""

    def open_position(position_id: str) -> None:
        item = saved.get(username, position_id)
        if item is None:
            return
        try:
            session.replace_position(saved.from_dict(item.data))
        except ValueError:
            ui.notify("Questa posizione salvata è danneggiata", type="negative")
            return
        ui.navigate.to("/")

    def remove(position_id: str, name: str) -> None:
        saved.delete(username, position_id)
        ui.notify(f"Eliminata «{name}»")
        listing.refresh()

    @ui.refreshable
    def listing() -> None:
        items = saved.list_for(username)
        with ui.card().classes(CARD):
            card_title(
                "Posizioni salvate",
                "bookmarks",
                subtitle=f"{len(items)} su {saved.MAX_PER_USER} disponibili",
            )
            if not items:
                ui.label(
                    "Non hai ancora salvato nessuna posizione. Nel simulatore, il "
                    "riquadro «Le mie posizioni» ha il pulsante «Salva»."
                ).classes(FAINT)
                ui.button(
                    "Vai al simulatore",
                    icon="candlestick_chart",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("unelevated no-caps").classes("mt-2 self-start")
                return
            with ui.row().classes("w-full gap-2 no-wrap sim-thead px-1 max-sm:hidden"):
                ui.label("Nome").classes("grow")
                ui.label("Sottostante").classes("w-28")
                ui.label("Stile").classes("w-24")
                ui.label("Salvata il").classes("w-36")
                ui.label("").classes("w-20")
            for item in items:
                with ui.row().classes("w-full gap-2 no-wrap items-center py-2 sim-divider px-1"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item.name).classes("text-sm font-medium t-text truncate")
                        ui.label(
                            f"{item.leg_count} gamb{'a' if item.leg_count == 1 else 'e'}"
                        ).classes("text-[11px] t-faint")
                    ui.label(item.ticker).classes("w-28 text-sm t-text2 max-sm:hidden")
                    ui.label("europea" if item.exercise == "european" else "americana").classes(
                        "w-24 text-xs t-muted max-sm:hidden"
                    )
                    ui.label(format_timestamp(item.saved_at)).classes(
                        "w-36 text-xs t-muted t-num max-sm:hidden"
                    )
                    with ui.row().classes("w-20 gap-0 no-wrap justify-end"):
                        ui.button(
                            icon="open_in_new",
                            on_click=lambda _, i=item.position_id: open_position(i),
                        ).props("flat dense round size=sm color=primary").tooltip(
                            "Apri nel simulatore"
                        )
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda _, i=item.position_id, n=item.name: remove(i, n),
                        ).props("flat dense round size=sm").classes("t-faint").tooltip("Elimina")

    listing()


def _password_card(user: auth.User) -> None:
    with ui.card().classes(CARD):
        card_title("Cambia password", "key")
        if user.default_password:
            ui.label("Questo account usa ancora la password predefinita.").classes(DANGER)

        current = (
            ui.input("Password attuale", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        new = (
            ui.input("Nuova password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        repeat = (
            ui.input("Ripeti la nuova password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        error = ui.label("").classes("text-xs t-loss")

        def submit() -> None:
            problem = auth.change_password(
                user.username, current.value or "", new.value or "", repeat.value or ""
            )
            if problem is not None:
                error.set_text(problem)
                return
            ui.notify("Password aggiornata", type="positive")
            ui.navigate.to("/account")

        repeat.on("keydown.enter", submit)
        ui.button("Aggiorna password", on_click=submit).props("unelevated no-caps").classes(
            "w-full py-2"
        )
