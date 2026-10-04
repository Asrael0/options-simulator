"""Server start-up.

The pattern used throughout the application:

1. ``@ui.page("/path")`` registers a route. The function runs from scratch on
   every visit, for every browser tab.
2. The position state does NOT live inside the page — it would last a single
   visit. It lives in ``session.py``, keyed by browser session, so it survives
   moving between pages.
3. Panels are ``@ui.refreshable`` functions registered in a ``PageContext``,
   which recomputes the analytics ONCE and then refreshes everything.
"""

from __future__ import annotations

from nicegui import ui

from . import auth
from . import pages as _pages  # noqa: F401

DEFAULT_PORT = 8080


def main() -> None:
    """Start the server and open the browser."""
    auth.migrate_legacy_data_dir()
    auth.ensure_default_admin()

    ui.run(
        title="Options Simulator",
        favicon="📈",
        dark=True,
        reload=False,
        port=DEFAULT_PORT,
        show=True,
        host="127.0.0.1",
        storage_secret=auth.storage_secret(),
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
