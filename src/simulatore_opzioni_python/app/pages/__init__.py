"""Registrazione delle pagine.

--- COSA FA QUESTO FILE ---
Importa i moduli delle pagine: l'import esegue i decoratori `@ui.page` e
registra così tutti gli indirizzi del sito.
"""

from . import access, admin, guide, report, simulator

__all__ = ["access", "admin", "guide", "report", "simulator"]
