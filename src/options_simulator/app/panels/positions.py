"""Pannello «Le mie posizioni»: salva, riapri, esporta e importa."""

from __future__ import annotations

from datetime import date

from nicegui import events, ui

from .. import auth, saved, session
from ..context import PageContext
from ..strategies import (
    STRATEGIES,
)
from ..tickers import display_symbol
from ..widgets import (
    CARD,
    FAINT,
    card_title,
)


def load_saved_into(ctx: PageContext, position_id: str) -> None:
    """Sostituisce la posizione della pagina con una salvata."""
    username = auth.current_username()
    item = saved.get(username, position_id) if username else None
    if item is None:
        ui.notify("Posizione non trovata", type="warning")
        return
    try:
        state = saved.from_dict(item.data)
    except ValueError:
        ui.notify("Questa posizione salvata è danneggiata", type="negative")
        return
    session.replace_position(state)
    ctx.state = state
    ui.notify(f"Aperta «{item.name}»", type="positive")
    ctx.rerender()


def saved_panel(ctx: PageContext) -> None:
    username = auth.current_username()
    if username is None:
        return
    items = saved.list_for(username)

    with ui.dialog() as dialog, ui.card().classes("sim-card w-[400px] max-w-full gap-3"):
        card_title("Salva la posizione", "bookmark_add")
        name = (
            ui.input(
                "Nome",
                value=f"{ctx.state.ticker} · {STRATEGIES[ctx.state.strategy_key].name}"
                if ctx.state.strategy_key in STRATEGIES
                else ctx.state.ticker,
            )
            .classes("w-full")
            .props("dense outlined autofocus")
        )
        ui.label(
            "Se usi un nome già salvato, la posizione con quel nome viene aggiornata."
        ).classes(FAINT)
        error = ui.label("").classes("text-xs t-loss")

        def confirm() -> None:
            problem = saved.save(username, name.value or "", ctx.state)
            if problem is not None:
                error.set_text(problem)
                return
            dialog.close()
            ui.notify("Posizione salvata", type="positive")
            ctx.rerender()

        name.on("keydown.enter", confirm)
        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Annulla", on_click=dialog.close).props("flat no-caps").classes("t-muted")
            ui.button("Salva", icon="check", on_click=confirm).props("unelevated no-caps")

    async def import_file(e: events.UploadEventArguments) -> None:
        try:
            imported_name, state = saved.import_bytes(await e.file.read())
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        session.replace_position(state)
        ctx.state = state
        ui.notify(f"Importata «{imported_name}». Premi «Salva» per tenerla.", type="positive")
        ctx.rerender()

    def export_file() -> None:
        filename = f"{ctx.state.ticker or 'posizione'}-{date.today().isoformat()}.json"
        ui.download.content(saved.export_bytes(name.value or ctx.state.ticker, ctx.state), filename)

    with ui.dialog() as import_dialog, ui.card().classes("sim-card w-[420px] max-w-full gap-3"):
        card_title("Importa una posizione", "upload_file")
        ui.label(
            "Scegli un file .json esportato dal simulatore (anche da un altro computer)."
        ).classes(FAINT)
        ui.upload(on_upload=import_file, auto_upload=True, max_file_size=1_000_000).props(
            'accept=".json" flat bordered color=primary'
        ).classes("w-full")
        ui.button("Chiudi", on_click=import_dialog.close).props("flat no-caps").classes(
            "self-end t-muted"
        )

    with ui.card().classes(CARD):
        card_title(
            "Le mie posizioni",
            "bookmarks",
            subtitle=f"{len(items)} salvat{'a' if len(items) == 1 else 'e'}",
            action=("Salva", "bookmark_add", dialog.open),
        )
        with ui.row().classes("w-full gap-2 -mt-1 mb-1"):
            ui.button("Esporta file", icon="download", on_click=export_file).props(
                "outline dense no-caps color=primary"
            ).classes("text-xs px-2")
            ui.button("Importa file", icon="upload", on_click=import_dialog.open).props(
                "outline dense no-caps color=primary"
            ).classes("text-xs px-2")
        if not items:
            ui.label(
                "Nessuna posizione salvata. Costruisci una strategia e premi «Salva» "
                "per ritrovarla in seguito, anche dopo aver spento il simulatore."
            ).classes(FAINT)
            return
        with ui.column().classes("w-full gap-0"):
            for item in items[:5]:
                with ui.row().classes("w-full items-center gap-2 no-wrap py-1.5 sim-divider"):
                    with ui.column().classes("gap-0 grow min-w-0"):
                        ui.label(item.name).classes("text-sm t-text truncate")
                        ui.label(
                            f"{display_symbol(item.ticker)} · {item.leg_count} "
                            f"gamb{'a' if item.leg_count == 1 else 'e'}"
                        ).classes("text-[11px] t-faint")
                    ui.button(
                        icon="open_in_new",
                        on_click=lambda _, i=item.position_id: load_saved_into(ctx, i),
                    ).props("flat dense round size=sm color=primary").tooltip("Apri")
        ui.link(
            "Gestiscile tutte nel tuo account →"
            if len(items) > 5
            else "Gestisci nel tuo account →",
            "/account",
        ).classes("text-xs t-accent no-underline mt-auto pt-1")
