"""Avvio del server.

COME FUNZIONA NICEGUI — vale la pena capirlo una volta sola.

È un framework "server-side": il codice Python gira sul server, il browser
mostra il risultato, e i due si parlano via WebSocket. Quando muovi uno slider
il browser manda l'evento al Python, il Python ricalcola e rimanda solo ciò che
è cambiato. Per questo si scrive come Python normale: non esiste un
"componente" con un ciclo di vita da imparare, esistono funzioni che disegnano.

Il pattern usato in questa applicazione:

1. ``@ui.page("/percorso")`` registra una rotta. La funzione viene eseguita da
   capo a ogni visita, per ogni scheda del browser.
2. Lo stato della posizione NON vive dentro la pagina — vivrebbe per una sola
   visita. Sta in ``session.py``, indicizzato per sessione del browser, così
   navigando fra le pagine si ritrova.
3. I pannelli sono ``@ui.refreshable`` registrati in un ``PageContext``, che
   ricalcola le analytics UNA volta e poi aggiorna tutto.
"""

from __future__ import annotations

from nicegui import ui

from . import auth
from . import pages as _pages  # noqa: F401  (l'import registra le rotte)

DEFAULT_PORT = 8080


def main() -> None:
    """Avvia il server e apre il browser."""
    auth.ensure_default_admin()

    ui.run(
        title="Simulatore di Opzioni",
        favicon="📈",
        dark=True,
        reload=False,
        port=DEFAULT_PORT,
        show=True,
        # In ascolto solo su questo computer. Cambiarlo espone l'applicazione
        # alla rete locale, e a quel punto la password di admin conta davvero.
        host="127.0.0.1",
        storage_secret=auth.storage_secret(),
    )


# --- `if __name__ == "__main__"`: eseguito o importato? --------------------
# Ogni modulo ha una variabile automatica `__name__`. Vale:
#   - il nome del modulo, se è stato IMPORTATO da qualcun altro;
#   - la stringa "__main__", se è il file che è stato ESEGUITO direttamente.
#
# Questo `if` è quindi il modo standard di dire: "esegui questa parte solo se
# sono il programma principale, non se qualcuno mi sta importando". Senza,
# importare questo modulo per riusarne una funzione avvierebbe il server.
#
# `in {"__main__", "__mp_main__"}` controlla l'appartenenza a un insieme: il
# secondo nome serve perché NiceGUI può riavviarsi in un processo separato, e
# in quel caso il modulo principale si chiama "__mp_main__" (mp = multiprocessing).
if __name__ in {"__main__", "__mp_main__"}:
    main()
