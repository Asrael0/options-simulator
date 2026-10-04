"""Page registration.

Importing the page modules runs their ``@ui.page`` decorators, which registers
every route of the site.
"""

from . import access, admin, guide, market, portfolio_page, report, simulator

__all__ = ["access", "admin", "guide", "market", "portfolio_page", "report", "simulator"]
