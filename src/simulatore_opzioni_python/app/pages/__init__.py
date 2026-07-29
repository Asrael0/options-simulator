"""Registrazione delle pagine.

--- COSA FA QUESTO FILE ---
Sembra che non faccia niente: importa quattro moduli e li elenca. In realtà è
la riga che fa esistere tutti gli indirizzi del sito.

--- IMPORT ESEGUITO PER IL SUO EFFETTO ---
Di solito si importa qualcosa per USARLO: `from math import sqrt` serve perché
poi si scrive `sqrt(...)`. Qui no.

I decoratori `@ui.page("/percorso")` sono righe di codice come le altre, e
vengono eseguite quando il modulo che le contiene viene importato. È in quel
momento che NiceGUI prende nota della rotta. Senza questo import, i file
esisterebbero sul disco ma nessun indirizzo risponderebbe.

Si dice che l'import ha un "effetto collaterale" (side effect): non serve il
valore, serve che il codice giri. È un caso in cui la cosa è voluta e
documentata; in generale gli import con effetti nascosti sono da evitare,
perché rendono difficile capire cosa succede e quando.
"""

from . import access, admin, guide, simulator

# --- `__all__` QUI, E LA DIRETTIVA "noqa" ALTROVE --------------------------
# Come in pricing/__init__.py, `__all__` dichiara che questi nomi sono
# esportati di proposito e non import dimenticati.
#
# Nel file main.py trovi invece, accanto all'import di questo pacchetto, un
# commento che comincia con cancelletto seguito da "noqa: F401". Sta per "no
# quality assurance": dice al linter di tacere su QUELLA riga, e il codice dopo
# i due punti indica quale regola ignorare (F401 = "importato ma mai usato").
#
# Va usato sempre con un codice preciso e con la spiegazione del perché: la
# stessa direttiva senza codice zittisce tutto, comprese le segnalazioni utili.
#
# Curiosità utile: ruff cerca quella sequenza in QUALUNQUE commento, anche in
# uno che voglia solo parlarne. È il motivo per cui qui sopra è scritta a
# parole invece che per esteso — altrimenti il linter la prenderebbe sul serio.
__all__ = ["access", "admin", "guide", "simulator"]
