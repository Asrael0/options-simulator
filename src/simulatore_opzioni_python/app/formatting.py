"""Formattazione numerica in locale italiano.

Gli estremi illimitati non vanno mai mostrati come ``inf`` né, peggio, come un
numero finito: ``payoff_bounds()`` li distingue apposta.

NOTA DI PYTHON — non si usa il modulo ``locale`` della libreria standard:
richiede che la locale italiana sia installata sul sistema operativo, cambia
uno stato GLOBALE del processo e non è thread-safe. Con poche regole (punto
per le migliaia, virgola per i decimali) è più affidabile scriverle a mano.
"""

from __future__ import annotations

import math

UNLIMITED_PROFIT = "illimitato"
UNLIMITED_LOSS = "illimitata"


def format_number(value: float, decimals: int = 2) -> str:
    """Numero in stile italiano: 1.234,56."""
    if not math.isfinite(value):
        return "—"
    # Il formato inglese usa la virgola per le migliaia e il punto per i
    # decimali: si scambiano i due caratteri passando per un segnaposto.
    english = f"{value:,.{decimals}f}"
    return english.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def format_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    if not math.isfinite(value):
        return "—"
    return f"{symbol} {format_number(value, decimals)}"


def format_signed_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Importo col segno esplicito.

    Il segno è informazione, non decorazione: la regola di accessibilità è che
    profitto e perdita non si distinguano mai per il solo colore.
    """
    if value == math.inf:
        return UNLIMITED_PROFIT
    if value == -math.inf:
        return UNLIMITED_LOSS
    if not math.isfinite(value):
        return "—"
    sign = "+" if value >= 0 else "−"
    return f"{sign} {symbol} {format_number(abs(value), decimals)}"


def format_percent(decimal: float, decimals: int = 0) -> str:
    """Da decimale a percentuale leggibile: 0.30 -> "30 %"."""
    if not math.isfinite(decimal):
        return "—"
    return f"{format_number(decimal * 100, decimals)} %"
