"""La pagina delle opzioni reali (`/mercato`), divisa per schede.

Importare il pacchetto registra la pagina: il decoratore `@ui.page` sta in
`page.py`. Gli altri file disegnano una scheda ciascuno.
"""

from __future__ import annotations

from .page import market_page

__all__ = ["market_page"]
