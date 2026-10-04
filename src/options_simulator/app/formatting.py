"""Formattazione di numeri e date, in italiano o in inglese.

--- COSA FA QUESTO FILE ---
Trasforma numeri in testo leggibile nella lingua scelta: in italiano `1234.5`
diventa `1.234,50` (punto per le migliaia, virgola per i decimali), in inglese
`1,234.50`. Lo stesso per le date: `12/10/2026` oppure `12 Oct 2026`.
Nient'altro: nessun calcolo, nessuna interfaccia.

Gli estremi illimitati non vanno mai mostrati come ``inf`` né, peggio, come un
numero finito: ``payoff_bounds()`` li distingue apposta.

NOTA — non si usa il modulo ``locale`` della libreria standard: richiede che
la locale italiana sia installata sul sistema operativo, cambia uno stato
GLOBALE del processo e non è thread-safe. Con poche regole è più affidabile
scriverle a mano.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from .i18n import current_lang, tr


def format_number(value: float, decimals: int = 2) -> str:
    """Numero nella lingua corrente: 1.234,56 (italiano) o 1,234.56 (inglese)."""
    if not math.isfinite(value):
        return "—"

    english = f"{value:,.{decimals}f}"
    if current_lang() == "en":
        return english

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
    if value == math.inf:
        return tr("illimitato")
    if value == -math.inf:
        return tr("illimitata")
    if not math.isfinite(value):
        return "—"
    sign = "+" if value >= 0 else "−"
    return f"{sign} {symbol} {format_number(abs(value), decimals)}"


def format_percent(decimal: float, decimals: int = 0) -> str:
    """Da decimale a percentuale leggibile: 0.30 -> "30 %"."""
    if not math.isfinite(decimal):
        return "—"
    number = format_number(decimal * 100, decimals)
    return f"{number}%" if current_lang() == "en" else f"{number} %"


WEEKDAYS = {
    "it": ["lun", "mar", "mer", "gio", "ven", "sab", "dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date(day: date) -> str:
    """Data nella lingua corrente: ``12/10/2026`` o ``12 Oct 2026``."""
    if current_lang() == "en":
        return f"{day.day} {MONTHS_EN[day.month - 1]} {day.year}"
    return day.strftime("%d/%m/%Y")


def format_short_date(day: date, *, year: bool = False) -> str:
    """Giorno e mese: ``12/10`` o ``12 Oct``; con ``year`` anche l'anno a due cifre."""
    if current_lang() == "en":
        text = f"{day.day} {MONTHS_EN[day.month - 1]}"
        return f"{text} {day.strftime('%y')}" if year else text
    return day.strftime("%d/%m/%y" if year else "%d/%m")


def expiry_date(days: float, today: date | None = None) -> date:
    """Data che cade fra ``days`` giorni."""
    return (today or date.today()) + timedelta(days=round(max(days, 0.0)))


def format_expiry(days: float, today: date | None = None) -> str:
    """Giorni alla scadenza come data, es. ``lun 12/10/2026``."""
    when = expiry_date(days, today)
    return f"{WEEKDAYS[current_lang()][when.weekday()]} {format_date(when)}"


def format_timestamp(iso: str) -> str:
    """Data salvata in UTC (``2026-10-03T13:35:19+00:00``) mostrata in ora locale.

    Un testo non riconoscibile viene restituito com'è, invece di far fallire
    la pagina.
    """
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    local = moment.astimezone()
    return f"{format_date(local.date())} {local.strftime('%H:%M')}"
