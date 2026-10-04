"""Number and date formatting, in Italian or English.

Turns numbers into readable text in the chosen language: in Italian ``1234.5``
becomes ``1.234,50`` (dot for thousands, comma for decimals), in English
``1,234.50``. Dates likewise: ``12/10/2026`` or ``12 Oct 2026``. Nothing else:
no calculations, no interface.

Unlimited extremes are never shown as ``inf`` or, worse, as a finite number:
``payoff_bounds()`` tells them apart on purpose.

NOTE — the standard ``locale`` module is not used: it needs the locale to be
installed on the operating system, changes GLOBAL process state and is not
thread-safe. With so few rules, writing them by hand is more reliable.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from .i18n import current_lang, tr


def format_number(value: float, decimals: int = 2) -> str:
    """Number in the current language: 1.234,56 (Italian) or 1,234.56 (English)."""
    if not math.isfinite(value):
        return "—"

    english = f"{value:,.{decimals}f}"
    if current_lang() == "en":
        return english

    return english.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def format_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Amount with a currency symbol, without an explicit sign."""
    if not math.isfinite(value):
        return "—"
    return f"{symbol} {format_number(value, decimals)}"


def format_signed_money(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """Amount with an explicit sign.

    The sign is information, not decoration: the accessibility rule is that
    profit and loss are never told apart by colour alone.
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
    """Decimal to readable percentage: 0.30 -> "30 %" (Italian) or "30%" (English)."""
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
    """Date in the current language: ``12/10/2026`` or ``12 Oct 2026``."""
    if current_lang() == "en":
        return f"{day.day} {MONTHS_EN[day.month - 1]} {day.year}"
    return day.strftime("%d/%m/%Y")


def format_short_date(day: date, *, year: bool = False) -> str:
    """Day and month: ``12/10`` or ``12 Oct``; with ``year`` also the two-digit year."""
    if current_lang() == "en":
        text = f"{day.day} {MONTHS_EN[day.month - 1]}"
        return f"{text} {day.strftime('%y')}" if year else text
    return day.strftime("%d/%m/%y" if year else "%d/%m")


def expiry_date(days: float, today: date | None = None) -> date:
    """Date ``days`` days from today."""
    return (today or date.today()) + timedelta(days=round(max(days, 0.0)))


def format_expiry(days: float, today: date | None = None) -> str:
    """Days to expiry as a date, e.g. ``Mon 12 Oct 2026``."""
    when = expiry_date(days, today)
    return f"{WEEKDAYS[current_lang()][when.weekday()]} {format_date(when)}"


def format_timestamp(iso: str) -> str:
    """UTC timestamp (``2026-10-03T13:35:19+00:00``) shown in local time.

    Unrecognised text is returned as it is instead of breaking the page.
    """
    try:
        moment = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    local = moment.astimezone()
    return f"{format_date(local.date())} {local.strftime('%H:%M')}"
