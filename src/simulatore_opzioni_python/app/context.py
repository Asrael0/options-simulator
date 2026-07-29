"""Contesto di pagina: tiene insieme stato, valori derivati e aggiornamento.

--- COSA FA QUESTO FILE ---
È il motore dell'aggiornamento dell'interfaccia, e il posto dove sta "la magia"
di NiceGUI. Vale la pena capirlo, perché tutto il resto ne dipende.

Il problema: una pagina mostra otto pannelli che dipendono tutti dagli stessi
numeri. Muovendo uno slider devono aggiornarsi tutti. Se ognuno ricalcolasse
per conto suo, un movimento costerebbe otto ricalcoli invece di uno.

La soluzione: `PageContext` tiene lo stato, i numeri derivati, e un ELENCO dei
pannelli disegnati. Quando qualcosa cambia, `rerender()` ricalcola UNA volta e
poi dice a ogni pannello di ridisegnarsi leggendo il risultato già pronto.

--- LA CLASSE SCRITTA A MANO ---
Fin qui tutte le classi erano `@dataclass`. Questa no: è scritta a mano, col
suo `__init__`. Perché? Perché una dataclass è pensata per CONTENERE DATI,
mentre qui ci sono anche comportamento e stato interno che si costruisce da
solo. Quando una classe fa più che custodire campi, `class` normale è più
onesta.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from nicegui import ui

from .state import Analytics, PositionState, compute

# --- RIFERIMENTO IN AVANTI: il nome del tipo fra virgolette ----------------
# `"PageContext"` è scritto come STRINGA perché la classe è definita più sotto:
# a questo punto del file il nome non esiste ancora. Mettendolo fra virgolette
# Python non prova a risolverlo subito, e mypy ci arriva comunque.
# (Grazie a `from __future__ import annotations` spesso non servirebbe, ma
# dentro un alias di tipo come questo sì.)
#: Un pannello è una funzione che disegna se stessa leggendo il contesto.
PanelRenderer = Callable[["PageContext"], None]
#: Un costruttore di grafico produce il dizionario di opzioni ECharts.
ChartBuilder = Callable[[PositionState, Analytics], dict[str, Any]]


class PageContext:
    """Stato + analytics + registro dei pannelli da aggiornare."""

    # --- `__init__`: il costruttore ----------------------------------------
    # Metodo speciale (i "dunder", doppio underscore prima e dopo) che Python
    # chiama automaticamente quando si crea l'oggetto: `PageContext(stato)`
    # esegue questo codice con `state=stato`.
    #
    # Il suo compito è riempire l'oggetto: ogni `self.qualcosa = ...` crea un
    # attributo che vivrà finché vive l'oggetto. È esattamente ciò che
    # `@dataclass` scriveva al posto nostro nei file precedenti.
    def __init__(self, state: PositionState) -> None:
        self.state = state
        self.analytics: Analytics = compute(state)
        # L'underscore iniziale segnala "attributo interno": i pannelli e i
        # grafici registrati non riguardano chi usa la classe.
        self._panels: list[Any] = []
        # `tuple[A, B]` è una coppia: due valori di tipo diverso tenuti
        # insieme. A differenza di una lista, ha lunghezza fissa e non si
        # modifica.
        self._charts: list[tuple[ui.echart, ChartBuilder]] = []

    def panel(self, render: PanelRenderer) -> None:
        """Disegna un pannello e lo registra per gli aggiornamenti futuri."""
        # --- `functools.partial`: pre-riempire un argomento -----------------
        # `ui.refreshable` vuole una funzione SENZA argomenti, ma i pannelli
        # hanno bisogno del contesto per sapere cosa disegnare.
        #
        # `partial(render, self)` costruisce una NUOVA funzione che, quando
        # verrà chiamata senza argomenti, eseguirà `render(self)`. È come
        # scrivere `lambda: render(self)`, ma più esplicito e leggermente più
        # veloce.
        #
        # `ui.refreshable(f)` è la parte NiceGUI: avvolge la funzione ricordando
        # in quale punto della pagina ha disegnato. Chiamando `.refresh()` più
        # tardi, cancella quel pezzo e lo ridisegna coi dati nuovi — senza
        # ricaricare la pagina e senza toccare il resto.
        refreshable = ui.refreshable(partial(render, self))
        self._panels.append(refreshable)
        # Prima chiamata: disegna davvero il pannello. Senza questa riga il
        # pannello sarebbe registrato ma invisibile.
        refreshable()

    def chart(self, builder: ChartBuilder, classes: str) -> ui.echart:
        element = ui.echart(builder(self.state, self.analytics)).classes(classes)
        self._charts.append((element, builder))
        return element

    def rerender(self) -> None:
        """Ricalcola una volta sola, poi aggiorna tutto ciò che è registrato."""
        # QUESTA è l'unica riga che chiama il motore di pricing per un'intera
        # interazione dell'utente. Tutto il resto legge il risultato.
        self.analytics = compute(self.state)
        # Scorrere una lista di tuple spacchettandole al volo: `element` prende
        # il primo valore di ogni coppia, `builder` il secondo.
        for element, builder in self._charts:
            element.options.clear()
            element.options.update(builder(self.state, self.analytics))
            element.update()
        for refreshable in self._panels:
            refreshable.refresh()
