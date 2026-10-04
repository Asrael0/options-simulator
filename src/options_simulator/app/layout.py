"""Cornice comune delle pagine: barra laterale, titolo, avvisi.

--- COSA FA QUESTO FILE ---
Ogni pagina del sito ha lo stesso contorno: barra laterale a sinistra coi
collegamenti, l'utente collegato in fondo, il titolo della pagina e l'avviso
sui prezzi. Questo file lo costruisce una volta sola, così nessuna pagina può
dimenticarsene o scriverlo in modo diverso.

Sui telefoni la barra laterale si nasconde e compare una sottile barra in alto
con il pulsante ☰ per aprirla.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import app, ui

from . import auth
from .i18n import LANGUAGES, current_lang, set_lang, tr
from .theme import apply_theme
from .widgets import DANGER_STRIP, ICON_TONES, didactic_notice

# percorso -> (etichetta, icona, titolo della pagina). Le scritte sono in
# italiano e passano da tr() quando si disegnano.
NAV_PAGES: list[tuple[str, str, str, str]] = [
    ("/", "Simulatore", "candlestick_chart", "Simulatore"),
    ("/mercato", "Opzioni reali", "travel_explore", "Opzioni reali"),
    ("/portafoglio", "Portafoglio", "account_balance_wallet", "Portafoglio virtuale"),
    ("/guida", "Guida", "menu_book", "Guida"),
]
ADMIN_PAGE = ("/admin", "Amministrazione", "admin_panel_settings", "Amministrazione")
SETTINGS_PAGE = ("/impostazioni", "Impostazioni", "settings", "Impostazioni")


def _page_title(path: str) -> str:
    for page in [*NAV_PAGES, ADMIN_PAGE, SETTINGS_PAGE]:
        if page[0] == path:
            return tr(page[3])
    return tr("Simulatore")


def _brand() -> None:
    name, tagline = (
        ("Options", "Simulator") if current_lang() == "en" else ("Simulatore", "di opzioni")
    )
    with ui.row().classes("items-center gap-2.5 no-wrap"):
        with ui.element("div").classes("sim-logo"):
            ui.icon("ssid_chart", size="20px")
        with ui.column().classes("gap-0"):
            ui.label(name).classes("t-serif text-[17px] font-semibold t-text leading-tight")
            ui.label(tagline).classes("text-[11px] t-muted leading-tight")


def _nav_item(path: str, label: str, icon: str, current: str) -> None:
    active = " active" if path == current else ""
    with ui.link(target=path).classes("sim-nav-item" + active):
        ui.icon(icon)
        ui.label(tr(label))


def _sidebar(current_path: str, user: auth.User | None) -> None:
    with ui.column().classes("w-full h-full p-3 gap-1 no-wrap"):
        with ui.row().classes("px-2 pt-2 pb-4"):
            _brand()

        ui.label(tr("Strumenti")).classes("sim-nav-section")
        for path, label, icon, _ in NAV_PAGES:
            _nav_item(path, label, icon, current_path)
        if user is not None and user.is_admin:
            ui.label(tr("Gestione")).classes("sim-nav-section")
            _nav_item(*ADMIN_PAGE[:3], current_path)

        ui.space()

        # Lingua, tema, colore e account stanno tutti nelle Impostazioni.
        _nav_item(*SETTINGS_PAGE[:3], current_path)

        if user is not None and user.is_admin:
            with (
                ui.element("button")
                .classes("sim-nav-item cursor-pointer")
                .on("click", _confirm_shutdown)
            ):
                ui.icon("power_settings_new")
                ui.label(tr("Spegni simulatore"))

        if user is not None:
            with ui.row().classes("w-full items-center gap-2.5 no-wrap sim-user mt-1"):
                ui.label(user.username[:1].upper()).classes("sim-avatar")
                with (
                    ui.link(target=SETTINGS_PAGE[0])
                    .classes("grow min-w-0 no-underline")
                    .tooltip(tr("Impostazioni")),
                    ui.column().classes("gap-0"),
                ):
                    ui.label(user.username).classes("text-sm font-semibold t-text truncate")
                    ui.label(tr("amministratore") if user.is_admin else tr("utente")).classes(
                        "text-[11px] t-accent" if user.is_admin else "text-[11px] t-muted"
                    )
                ui.button(icon="logout", on_click=_logout).props(
                    "flat dense round size=sm"
                ).classes("t-muted").tooltip(tr("Esci"))


@contextmanager
def page_frame(current_path: str, *, subtitle: str = "", title: str = "") -> Iterator[None]:
    """Barra laterale, titolo e nota sui prezzi attorno al contenuto."""
    apply_theme()
    ui.page_title(f"{title or _page_title(current_path)} · {tr('Simulatore di opzioni')}")
    user = auth.current_user()

    drawer = ui.left_drawer(bordered=False).props("width=256 breakpoint=1023")
    with drawer:
        _sidebar(current_path, user)

    with (
        ui.header(elevated=False).classes("lg:hidden sim-topbar px-3 py-2"),
        ui.row().classes("w-full items-center gap-2 no-wrap"),
    ):
        ui.button(icon="menu", on_click=drawer.toggle).props("flat dense round").classes("t-text")
        _brand()

    with ui.column().classes("w-full max-w-[1440px] mx-auto px-4 lg:px-8 py-6 lg:py-8 gap-5"):
        with ui.column().classes("gap-1 mb-1"):
            ui.label(title or _page_title(current_path)).classes("sim-h1")
            if subtitle:
                ui.label(subtitle).classes("text-sm t-muted")

        if user is not None and user.is_admin and user.default_password:
            with ui.row().classes(DANGER_STRIP):
                ui.icon("warning", size="18px")
                ui.label(
                    tr(
                        "Password admin predefinita: va bene in locale, cambiala prima "
                        "di rendere il sito raggiungibile da altri."
                    )
                ).classes("grow")
                ui.link(tr("Cambiala"), SETTINGS_PAGE[0]).classes("font-semibold t-loss")

        yield

        # In fondo e non in cima: resta su ogni pagina senza spingere giù il
        # contenuto che si è venuti a usare.
        didactic_notice()


def _confirm_shutdown() -> None:
    """Chiede conferma e spegne il server.

    Serve perché il simulatore parte senza finestra: senza questo pulsante
    resterebbe acceso finché non si riavvia il computer.
    """
    with ui.dialog() as dialog, ui.card().classes("sim-card w-[380px] max-w-full gap-3"):
        ui.label(tr("Spegnere il simulatore?")).classes("sim-card-title")
        ui.label(
            tr(
                "Il sito smette di funzionare finché non lo riavvii dal collegamento "
                "sul desktop. Le posizioni salvate restano; quella aperta, se non "
                "l'hai salvata, si perde."
            )
        ).classes("text-sm t-muted")
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(tr("Annulla"), on_click=dialog.close).props("flat no-caps").classes("t-muted")
            ui.button(tr("Spegni"), icon="power_settings_new", on_click=_shutdown).props(
                "unelevated no-caps color=negative"
            )
    dialog.open()


def _shutdown() -> None:
    ui.notify(tr("Simulatore spento. Puoi chiudere questa scheda."), type="info", timeout=0)
    # Un attimo di pausa perché il messaggio arrivi al browser prima che il
    # server si fermi.
    ui.timer(0.5, app.shutdown, once=True)


def _logout() -> None:
    auth.end_session()
    ui.navigate.to("/login")


HERO_POINTS: list[tuple[str, str, str]] = [
    ("functions", "Black-Scholes e albero binomiale", "Europee e americane, a confronto."),
    ("query_stats", "Greche e scenari", "Delta, gamma, theta, vega e vol crush."),
    ("school", "Pensato per imparare", "Ogni numero ha la sua spiegazione."),
]


@contextmanager
def centered_card(title: str, subtitle: str = "") -> Iterator[None]:
    """Cornice per le pagine di accesso e registrazione.

    Su schermi larghi è divisa in due: a sinistra una presentazione del
    simulatore, a destra il modulo. Sui telefoni resta solo il modulo.
    """
    apply_theme()
    ui.page_title(f"{title} · {tr('Simulatore di opzioni')}")
    with ui.row().classes("w-full min-h-screen no-wrap gap-0"):
        with ui.column().classes(
            "sim-hero w-[46%] max-md:hidden min-h-screen p-12 justify-between no-wrap"
        ):
            _brand()
            with ui.column().classes("gap-6 max-w-[460px]"):
                ui.label(tr("Capire le opzioni, una variabile alla volta.")).classes(
                    "t-serif text-[40px] leading-[1.1] t-text"
                ).style("font-weight: 500; letter-spacing: -0.015em")
                for icon, head, text in HERO_POINTS:
                    with ui.row().classes("items-start gap-3 no-wrap"):
                        with ui.element("div").classes(
                            f"sim-card-icon tone-{ICON_TONES.get(icon, 'accent')}"
                        ):
                            ui.icon(icon, size="18px")
                        with ui.column().classes("gap-0"):
                            ui.label(tr(head)).classes("text-sm font-semibold t-text")
                            ui.label(tr(text)).classes("text-sm t-muted")
            ui.label(tr("Prezzi teorici · dati reali da CBOE")).classes("text-xs t-faint")

        with (
            ui.column().classes("grow min-h-screen items-center justify-center p-6"),
            ui.column().classes("w-full max-w-[400px] gap-3"),
        ):
            # La lingua si sceglie anche prima di accedere.
            with ui.row().classes("w-full items-center no-wrap mb-4"):
                with ui.element("div").classes("md:hidden"):
                    _brand()
                ui.space()
                ui.toggle(
                    LANGUAGES, value=current_lang(), on_change=lambda e: set_lang(e.value)
                ).props("dense no-caps unelevated toggle-color=primary").classes("sim-seg")
            ui.label(title).classes("sim-h1")
            if subtitle:
                ui.label(subtitle).classes("text-sm t-muted -mt-1 mb-2")
            yield
