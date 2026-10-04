"""The real options page (``/market``), split by tab.

Importing the package registers the page: the ``@ui.page`` decorator is in
``page.py``. The other modules draw one tab each.
"""

from __future__ import annotations

from .page import market_page

__all__ = ["market_page"]
