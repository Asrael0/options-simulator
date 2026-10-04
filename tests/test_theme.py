"""Colore principale a scelta."""

from __future__ import annotations

from simulatore_opzioni_python.app.theme import ACCENTS, PALETTES, resolved_palette


def test_default_accent_keeps_base_palette() -> None:
    assert resolved_palette("dark") == {
        **PALETTES["dark"],
        "accent": ACCENTS["terracotta"]["dark"],
        "accent-soft": resolved_palette("dark")["accent-soft"],
        "accent-ink": "#ffffff",
    }


def test_blue_uses_cool_blacks_and_blue_accent() -> None:
    dark = resolved_palette("dark", "blu")
    assert dark["accent"] == ACCENTS["blu"]["dark"]
    assert dark["bg"] != PALETTES["dark"]["bg"]
    assert dark["accent-soft"].startswith("rgba(91,141,239")
    light = resolved_palette("light", "blu")
    assert light["accent"] == ACCENTS["blu"]["light"]


def test_unknown_accent_falls_back_to_default() -> None:
    assert resolved_palette("dark", "fucsia") == resolved_palette("dark")
