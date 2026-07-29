"""Cornice comune delle pagine: intestazione, navigazione, avvisi.

NOTA DI PYTHON — ``@contextmanager``.

``page_frame`` è un gestore di contesto: si usa con ``with``, esegue il codice
prima dello ``yield`` all'entrata e quello dopo all'uscita. Serve a garantire
che ogni pagina abbia la stessa intestazione e la stessa nota didattica senza
doverle ricopiare, e senza che una pagina possa dimenticarsene.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import ui

from . import auth
from .widgets import DANGER, didactic_notice

#: Percorso, etichetta, icona. L'ordine è quello della barra di navigazione.
NAV_PAGES: list[tuple[str, str, str]] = [
    ("/", "Posizione", "tune"),
    ("/payoff", "Payoff", "show_chart"),
    ("/greche", "Greche", "functions"),
    ("/scenari", "Scenari", "science"),
    ("/costi", "Costi", "payments"),
    ("/guida", "Guida", "school"),
]

ADMIN_PAGE = ("/admin", "Amministrazione", "admin_panel_settings")


def _nav_button(path: str, label: str, icon: str, current: str) -> None:
    active = path == current
    button = ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(path))
    button.props("flat dense no-caps" + ("" if active else " color=grey-6"))
    button.classes("text-xs" + (" font-bold" if active else ""))


@contextmanager
def page_frame(current_path: str, *, subtitle: str = "") -> Iterator[None]:
    """Intestazione, navigazione e nota didattica attorno al contenuto."""
    ui.dark_mode().enable()
    ui.query("body").style("background-color: #0a0c11")
    ui.add_head_html('<meta name="viewport" content="width=device-width, initial-scale=1">')

    user = auth.current_user()

    with (
        ui.header().classes("bg-[#11141c] border-b border-[#1e222d] px-4 py-2"),
        ui.row().classes("w-full max-w-[1500px] mx-auto items-center gap-3 no-wrap"),
    ):
        ui.label("Simulatore di Opzioni").classes("text-sm font-bold shrink-0")
        with ui.row().classes("gap-0 grow flex-wrap"):
            for path, label, icon in NAV_PAGES:
                _nav_button(path, label, icon, current_path)
            if user is not None and user.is_admin:
                _nav_button(*ADMIN_PAGE, current_path)
        if user is not None:
            with ui.row().classes("items-center gap-1 shrink-0 no-wrap"):
                ui.button(
                    user.username,
                    icon="person",
                    on_click=lambda: ui.navigate.to("/account"),
                ).props("flat dense no-caps color=grey-6").classes("text-xs")
                if user.is_admin:
                    ui.label("admin").classes(
                        "text-[10px] font-bold px-1 rounded border border-[#b07dff] text-[#b07dff]"
                    )
                ui.button(icon="logout", on_click=_logout).props(
                    "flat dense round size=sm color=grey-6"
                ).tooltip("Esci")

    with ui.column().classes("w-full max-w-[1500px] mx-auto p-4 gap-4"):
        if subtitle:
            ui.label(subtitle).classes("text-xs text-[#8b93a7] -mb-1")

        if user is not None and user.is_admin and user.default_password:
            ui.label(
                "⚠ L'account amministratore usa ancora la password predefinita. "
                "Va bene finché l'applicazione gira solo su questo computer. "
                "Se mai la esponi su una rete raggiungibile da altri, cambiala prima."
            ).classes(DANGER)

        didactic_notice()
        yield


def _logout() -> None:
    auth.end_session()
    ui.navigate.to("/login")


@contextmanager
def centered_card(title: str, subtitle: str = "") -> Iterator[None]:
    """Cornice per le pagine di accesso e registrazione."""
    ui.dark_mode().enable()
    ui.query("body").style("background-color: #0a0c11")
    with (
        ui.column().classes("w-full h-screen items-center justify-center p-4"),
        ui.card().classes(
            "w-full max-w-[420px] bg-[#11141c] border border-[#1e222d] rounded-xl p-6 gap-3"
        ),
    ):
        ui.label("Simulatore di Opzioni").classes("text-lg font-bold")
        ui.label(title).classes("text-sm text-[#c9cfdd]")
        if subtitle:
            ui.label(subtitle).classes("text-xs text-[#8b93a7]")
        yield
