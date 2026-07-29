"""Registrazione delle pagine.

Importare questi moduli è ciò che REGISTRA le pagine: i decoratori
``@ui.page(...)`` vengono eseguiti al momento dell'import. Senza questi
import le rotte non esisterebbero, anche se i file ci sono.
"""

from . import access, admin, guide, simulator

__all__ = ["access", "admin", "guide", "simulator"]
