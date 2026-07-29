"""Formattazione numerica in locale italiano.

--- COSA FA QUESTO FILE ---
Trasforma numeri in testo leggibile all'italiana: `1234.5` diventa `1.234,50`.
Punto per le migliaia, virgola per i decimali — l'opposto della convenzione
inglese. Nient'altro: nessun calcolo, nessuna interfaccia.

Gli estremi illimitati non vanno mai mostrati come ``inf`` né, peggio, come un
numero finito: ``payoff_bounds()`` li distingue apposta.

NOTA — non si usa il modulo ``locale`` della libreria standard: richiede che
la locale italiana sia installata sul sistema operativo, cambia uno stato
GLOBALE del processo e non è thread-safe. Con poche regole è più affidabile
scriverle a mano.
"""

from __future__ import annotations

import math

UNLIMITED_PROFIT = "illimitato"
UNLIMITED_LOSS = "illimitata"


def format_number(value: float, decimals: int = 2) -> str:
    """Numero in stile italiano: 1.234,56."""
    # `math.isfinite` è falso per infinito e per NaN. `not` lo nega.
    if not math.isfinite(value):
        return "—"

    # --- LE F-STRING E I MINI-FORMATI --------------------------------------
    # Una stringa preceduta da `f` permette di inserire espressioni dentro le
    # graffe: `f"ciao {nome}"` mette lì il valore di `nome`.
    #
    # Dopo i due punti dentro le graffe si può specificare COME formattare:
    #     {x:.2f}     due cifre decimali            -> 3.14
    #     {x:,.2f}    con separatore delle migliaia -> 1,234.56
    #     {x:>10}     allineato a destra in 10 spazi
    #     {x:.0%}     come percentuale
    #
    # Qui `decimals` è a sua volta una variabile, quindi si annida un secondo
    # gruppo di graffe: `{value:,.{decimals}f}`. Python risolve prima quelle
    # interne, poi applica il formato risultante.
    english = f"{value:,.{decimals}f}"

    # --- SCAMBIARE DUE CARATTERI: il trucco del segnaposto -----------------
    # `str.replace(vecchio, nuovo)` restituisce una NUOVA stringa: in Python le
    # stringhe sono immutabili, non si modificano sul posto.
    #
    # Il problema: per passare da 1,234.56 a 1.234,56 bisogna scambiare virgola
    # e punto. Farlo in due passaggi diretti non funziona — sostituendo prima
    # le virgole in punti si otterrebbe 1.234.56, e il secondo passaggio
    # cambierebbe anche quelli appena scritti.
    #
    # Soluzione: si passa da un carattere che non comparirà mai nel testo.
    # `\x00` è il carattere nullo, scritto in esadecimale. Tre sostituzioni
    # concatenate: ogni `.replace` lavora sul risultato della precedente.
    return english.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def format_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Importo con simbolo di valuta, senza segno esplicito."""
    if not math.isfinite(value):
        return "—"
    return f"{symbol} {format_number(value, decimals)}"


def format_signed_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Importo col segno esplicito.

    Il segno è informazione, non decorazione: la regola di accessibilità è che
    profitto e perdita non si distinguano mai per il solo colore.
    """
    # `math.inf` visto in payoff.py: qui si intercetta prima di formattare,
    # perché "inf" a schermo non significherebbe nulla per l'utente.
    if value == math.inf:
        return UNLIMITED_PROFIT
    if value == -math.inf:
        return UNLIMITED_LOSS
    if not math.isfinite(value):
        return "—"
    sign = "+" if value >= 0 else "−"
    # `abs()` toglie il segno dal numero, perché il segno lo si scrive a parte.
    return f"{sign} {symbol} {format_number(abs(value), decimals)}"


def format_percent(decimal: float, decimals: int = 0) -> str:
    """Da decimale a percentuale leggibile: 0.30 -> "30 %"."""
    if not math.isfinite(decimal):
        return "—"
    # Qui avviene la conversione annunciata in types.py: il motore lavora in
    # decimali, l'utente legge percentuali. Questa moltiplicazione per 100 è
    # l'unico punto in cui accade.
    return f"{format_number(decimal * 100, decimals)} %"
