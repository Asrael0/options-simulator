"""Login, sign-up and settings pages.

Three routes: ``/login``, ``/signup`` and ``/settings``. The first two are open
to visitors who are not logged in (otherwise nobody could ever log in); the
third requires login and gathers everything about the user: language, theme,
colour, saved positions, password and account details.
"""

from __future__ import annotations

from nicegui import ui

from .. import auth, saved, session
from ..formatting import format_timestamp
from ..i18n import LANGUAGES, current_lang, set_lang, tr, trn
from ..layout import SETTINGS_PAGE, centered_card, page_frame
from ..theme import ACCENTS, MODE_LABELS, current_accent, set_accent, set_theme_mode, theme_mode
from ..tickers import display_symbol
from ..widgets import CARD, DANGER, FAINT, MUTED, card_title


@ui.page("/login")
def login_page() -> None:
    with centered_card(tr("Accedi"), tr("Serve un account per usare il simulatore.")):
        username = ui.input(tr("Nome utente")).classes("w-full").props("dense outlined autofocus")
        password = (
            ui.input(tr("Password"), password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        error = ui.label("").classes("text-xs t-loss")

        def submit() -> None:
            user = auth.verify_credentials(username.value or "", password.value or "")
            if user is None:
                session.STATS.failed_logins += 1
                error.set_text(tr("Nome utente o password non corretti."))
                return
            auth.start_session(user)
            session.STATS.logins += 1
            session.touch(user.username)
            ui.navigate.to("/")

        password.on("keydown.enter", submit)
        username.on("keydown.enter", submit)

        ui.button(tr("Accedi"), on_click=submit).props("unelevated no-caps").classes(
            "w-full py-2 mt-1"
        )
        with ui.row().classes("w-full justify-center gap-1 items-center"):
            ui.label(tr("Non hai un account?")).classes(MUTED)
            ui.button(tr("Registrati"), on_click=lambda: ui.navigate.to("/signup")).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

        ui.separator()
        ui.label(
            tr(
                "Primo avvio: esiste già un account amministratore con nome utente "
                "«admin» e password «admin». Cambiala dalla pagina Impostazioni."
            )
        ).classes(FAINT)


@ui.page("/signup")
def signup_page() -> None:
    with centered_card(tr("Crea un account")):
        username = ui.input(tr("Nome utente")).classes("w-full").props("dense outlined autofocus")
        password = (
            ui.input(tr("Password"), password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        confirm = (
            ui.input(tr("Ripeti la password"), password=True, password_toggle_button=True)
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
            ui.notify(tr("Account creato: ora puoi accedere"), type="positive")
            ui.navigate.to("/login")

        confirm.on("keydown.enter", submit)

        ui.button(tr("Crea account"), on_click=submit).props("unelevated no-caps").classes(
            "w-full py-2 mt-1"
        )
        with ui.row().classes("w-full justify-center gap-1 items-center"):
            ui.label(tr("Hai già un account?")).classes(MUTED)
            ui.button(tr("Accedi"), on_click=lambda: ui.navigate.to("/login")).props(
                "flat dense no-caps color=primary"
            ).classes("text-xs")

        ui.separator()
        ui.label(
            tr(
                "Le password non vengono mai salvate in chiaro: il file contiene solo "
                "un hash pbkdf2 con 600.000 iterazioni e un sale casuale diverso per "
                "ogni utente."
            )
        ).classes(FAINT)


@ui.page("/settings")
def settings_page() -> None:
    if not auth.require_login():
        return
    user = auth.current_user()
    if user is None:
        ui.navigate.to("/login")
        return

    with (
        page_frame(
            SETTINGS_PAGE[0],
            subtitle=tr("Lingua, aspetto, posizioni salvate e dati del tuo accesso"),
        ),
        ui.row().classes("w-full gap-5 items-start no-wrap max-lg:flex-wrap"),
    ):
        with ui.column().classes("gap-5 grow min-w-0 w-full"):
            _appearance_card()
            _saved_positions(user.username)

        with ui.column().classes("gap-5 w-full lg:w-[420px] shrink-0"):
            _password_card(user)
            with ui.card().classes(CARD):
                card_title(tr("Dati dell'account"), "badge")
                for label, value in [
                    (tr("Nome utente"), user.username),
                    (tr("Ruolo"), tr("amministratore") if user.is_admin else tr("utente")),
                    (tr("Creato il"), format_timestamp(user.created_at)),
                ]:
                    with ui.row().classes("w-full justify-between text-sm py-2 sim-divider"):
                        ui.label(label).classes(MUTED)
                        ui.label(value).classes("t-text2")


def _appearance_card() -> None:
    """Language, theme and accent colour: every choice reloads the page."""
    with ui.card().classes(CARD):
        card_title(
            tr("Aspetto e lingua"),
            "palette",
            subtitle=tr("Le scelte restano salvate in questo browser."),
        )
        with ui.column().classes("w-full gap-4"):
            with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                ui.label(tr("Lingua")).classes("text-sm font-medium t-text w-24")
                ui.toggle(
                    LANGUAGES,
                    value=current_lang(),
                    on_change=lambda e: set_lang(e.value),
                ).props("dense no-caps unelevated toggle-color=primary").classes("sim-seg")

            with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                ui.label(tr("Tema")).classes("text-sm font-medium t-text w-24")
                ui.toggle(
                    {mode: tr(label) for mode, (label, _) in MODE_LABELS.items()},
                    value=theme_mode(),
                    on_change=lambda e: set_theme_mode(e.value),
                ).props("dense no-caps unelevated toggle-color=primary").classes("sim-seg")
                ui.label(tr("«Automatico» segue il tema di Windows.")).classes(FAINT)

            with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                ui.label(tr("Colore")).classes("text-sm font-medium t-text w-24")
                chosen = current_accent()
                with ui.row().classes("gap-2 no-wrap items-center"):
                    for key, accent in ACCENTS.items():
                        ui.element("button").classes(
                            "sim-swatch sim-swatch-lg" + (" active" if key == chosen else "")
                        ).style(f"background: {accent['dark']}").on(
                            "click", lambda _, k=key: set_accent(k)
                        ).tooltip(tr(accent["label"]))
                ui.label(tr(ACCENTS[chosen]["label"])).classes("text-sm t-muted")


def _saved_positions(username: str) -> None:
    """List of saved positions, with open and delete."""

    def open_position(position_id: str) -> None:
        item = saved.get(username, position_id)
        if item is None:
            return
        try:
            session.replace_position(saved.from_dict(item.data))
        except ValueError:
            ui.notify(tr("Questa posizione salvata è danneggiata"), type="negative")
            return
        ui.navigate.to("/")

    def remove(position_id: str, name: str) -> None:
        saved.delete(username, position_id)
        ui.notify(tr("Eliminata «{name}»", name=name))
        listing.refresh()

    @ui.refreshable
    def listing() -> None:
        items = saved.list_for(username)
        with ui.card().classes(CARD):
            card_title(
                tr("Posizioni salvate"),
                "bookmarks",
                subtitle=tr(
                    "{len} su {max_per_user} disponibili",
                    len=len(items),
                    max_per_user=saved.MAX_PER_USER,
                ),
            )
            if not items:
                ui.label(
                    tr(
                        "Non hai ancora salvato nessuna posizione. Nel simulatore, il "
                        "riquadro «Le mie posizioni» ha il pulsante «Salva»."
                    )
                ).classes(FAINT)
                ui.button(
                    tr("Vai al simulatore"),
                    icon="candlestick_chart",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("unelevated no-caps").classes("mt-2 self-start")
                return
            with ui.row().classes("w-full gap-2 no-wrap sim-thead px-1 max-sm:hidden"):
                ui.label(tr("Nome")).classes("grow")
                ui.label(tr("Sottostante")).classes("w-28")
                ui.label(tr("Stile")).classes("w-24")
                ui.label(tr("Salvata il")).classes("w-36")
                ui.label("").classes("w-20")
            for item in items:
                with ui.row().classes("w-full gap-2 no-wrap items-center py-2 sim-divider px-1"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item.name).classes("text-sm font-medium t-text truncate")
                        ui.label(trn("{n} gamba", "{n} gambe", item.leg_count)).classes(
                            "text-[11px] t-faint"
                        )
                    ui.label(display_symbol(item.ticker)).classes(
                        "w-28 text-sm t-text2 max-sm:hidden"
                    )
                    ui.label(
                        tr("europea") if item.exercise == "european" else tr("americana")
                    ).classes("w-24 text-xs t-muted max-sm:hidden")
                    ui.label(format_timestamp(item.saved_at)).classes(
                        "w-36 text-xs t-muted t-num max-sm:hidden"
                    )
                    with ui.row().classes("w-20 gap-0 no-wrap justify-end"):
                        ui.button(
                            icon="open_in_new",
                            on_click=lambda _, i=item.position_id: open_position(i),
                        ).props("flat dense round size=sm color=primary").tooltip(
                            tr("Apri nel simulatore")
                        )
                        ui.button(
                            icon="delete_outline",
                            on_click=lambda _, i=item.position_id, n=item.name: remove(i, n),
                        ).props("flat dense round size=sm").classes("t-faint").tooltip(
                            tr("Elimina")
                        )

    listing()


def _password_card(user: auth.User) -> None:
    with ui.card().classes(CARD):
        card_title(tr("Cambia password"), "key")
        if user.default_password:
            ui.label(tr("Questo account usa ancora la password predefinita.")).classes(DANGER)

        current = (
            ui.input(tr("Password attuale"), password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        new = (
            ui.input(tr("Nuova password"), password=True, password_toggle_button=True)
            .classes("w-full")
            .props("dense outlined")
        )
        repeat = (
            ui.input(tr("Ripeti la nuova password"), password=True, password_toggle_button=True)
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
            ui.notify(tr("Password aggiornata"), type="positive")
            ui.navigate.to(SETTINGS_PAGE[0])

        repeat.on("keydown.enter", submit)
        ui.button(tr("Aggiorna password"), on_click=submit).props("unelevated no-caps").classes(
            "w-full py-2"
        )
