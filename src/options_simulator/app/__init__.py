"""Interfaccia grafica del simulatore, basata su NiceGUI.

Questo pacchetto dipende da ``pricing``, mai il contrario: il motore resta
utilizzabile da un notebook o da qualunque altro frontend.
"""

from .main import main

__all__ = ["main"]
