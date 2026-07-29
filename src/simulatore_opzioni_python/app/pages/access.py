"""Pagine di accesso, registrazione e cambio password."""

from __future__ import annotations

from nicegui import ui

from .. import auth, session
from ..layout import centered_card, page_frame
from ..widgets import CARD, DANGER, FAINT, MUTED, TITLE


@ui.page("/login")
def login_page() -> None:
    with centered_card("Accedi", "Serve un account per usare il simulatore."):
        username = ui.input("Nome utente").classes("w-full").props("dense outlined autofocus")
        password = (
            ui.input("Password", password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        error = ui.label("").classes("text-xs text-[#ff5d6c]")

        def submit() -> None:
            user = auth.verify_credentials(username.value or "", password.value or "")
            if user is None:
                session.STATS.failed_logins += 1
                # Messaggio volutamente generico: dire "utente inesistente"
                # rivelerebbe quali nomi sono registrati.
                error.set_text("Nome utente o password non corretti.")
                return
            auth.start_session(user)
            session.STATS.logins += 1
            session.touch(user.username)
            ui.navigate.to("/")

        password.on("keydown.enter", submit)
        username.on("keydown.enter", submit)

        ui.button("Accedi", on_click=submit).props("no-caps").classes("w-full")
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
        error = ui.label("").classes("text-xs text-[#ff5d6c]")

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

        ui.button("Crea account", on_click=submit).props("no-caps").classes("w-full")
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

    with page_frame("/account", subtitle="Il tuo account"):
        with ui.card().classes(CARD + " max-w-[520px]"):
            ui.label("Cambia password").classes(TITLE)
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
            error = ui.label("").classes("text-xs text-[#ff5d6c]")

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
            ui.button("Aggiorna password", on_click=submit).props("no-caps").classes("w-full")

        with ui.card().classes(CARD + " max-w-[520px]"):
            ui.label("Dati dell'account").classes(TITLE)
            for label, value in [
                ("Nome utente", user.username),
                ("Ruolo", "amministratore" if user.is_admin else "utente"),
                ("Creato il", user.created_at),
            ]:
                with ui.row().classes("w-full justify-between text-xs"):
                    ui.label(label).classes(MUTED)
                    ui.label(value).classes("text-[#c9cfdd]")
