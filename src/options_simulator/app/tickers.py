"""Catalogue of the stocks suggested on the «Real options» page.

Just a list: symbol, name and category of about 150 stocks, ETFs and indices
with heavily traded options on CBOE. It feeds the search box and the category
buttons. Category and Italian names go through tr() when displayed.

It is not a limit: any US symbol with options works even if it is not listed,
it just has to be typed.

ONE SYMBOL, ONE SPELLING. CBOE writes indices in three ways: they are requested
as ``_SPX``, appear as ``SPX`` in option symbols and come back as ``^SPX`` in
the response. This module holds the program's single rule:
  - ``canonical_symbol`` gives the internal spelling, the one to request from
    CBOE (``_SPX`` for indices, ``AAPL`` for the rest);
  - ``display_symbol`` gives the spelling to show, always clean (``SPX``).
Whatever the user types (``spx``, ``_SPX``, ``^SPX``) ends up the same.
"""

from __future__ import annotations

from .i18n import tr

CATALOG: dict[str, list[tuple[str, str]]] = {
    "Indici": [
        ("_SPX", "S&P 500 (indice)"),
        ("_XSP", "Mini S&P 500 (1/10 di SPX)"),
        ("_NDX", "Nasdaq 100 (indice)"),
        ("_RUT", "Russell 2000 (indice)"),
        ("_DJX", "Dow Jones (1/100)"),
        ("_VIX", "VIX, indice della volatilità"),
    ],
    "ETF di mercato": [
        ("SPY", "SPDR S&P 500"),
        ("QQQ", "Invesco Nasdaq 100"),
        ("IWM", "iShares Russell 2000"),
        ("DIA", "SPDR Dow Jones"),
        ("VOO", "Vanguard S&P 500"),
        ("EEM", "iShares mercati emergenti"),
        ("EFA", "iShares mercati sviluppati ex USA"),
        ("FXI", "iShares Cina large cap"),
        ("EWZ", "iShares Brasile"),
        ("EWJ", "iShares Giappone"),
        ("EWI", "iShares Italia"),
        ("EWG", "iShares Germania"),
    ],
    "ETF di settore": [
        ("XLF", "Finanziari"),
        ("XLE", "Energia"),
        ("XLK", "Tecnologia"),
        ("XLV", "Sanità"),
        ("XLI", "Industriali"),
        ("XLY", "Consumi discrezionali"),
        ("XLP", "Beni di prima necessità"),
        ("XLU", "Utility"),
        ("XBI", "Biotecnologie"),
        ("SMH", "Semiconduttori"),
        ("KRE", "Banche regionali"),
        ("ARKK", "ARK Innovation"),
    ],
    "Materie prime e obbligazioni": [
        ("GLD", "Oro"),
        ("SLV", "Argento"),
        ("USO", "Petrolio"),
        ("UNG", "Gas naturale"),
        ("GDX", "Minatori d'oro"),
        ("TLT", "Treasury USA 20+ anni"),
        ("IEF", "Treasury USA 7-10 anni"),
        ("HYG", "Obbligazioni high yield"),
        ("LQD", "Obbligazioni societarie"),
    ],
    "Tecnologia": [
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("NVDA", "Nvidia"),
        ("GOOGL", "Alphabet (Google)"),
        ("AMZN", "Amazon"),
        ("META", "Meta Platforms"),
        ("TSLA", "Tesla"),
        ("AMD", "Advanced Micro Devices"),
        ("AVGO", "Broadcom"),
        ("INTC", "Intel"),
        ("QCOM", "Qualcomm"),
        ("MU", "Micron"),
        ("TSM", "Taiwan Semiconductor"),
        ("ORCL", "Oracle"),
        ("CRM", "Salesforce"),
        ("ADBE", "Adobe"),
        ("NFLX", "Netflix"),
        ("PLTR", "Palantir"),
        ("SNOW", "Snowflake"),
        ("SHOP", "Shopify"),
        ("UBER", "Uber"),
        ("ABNB", "Airbnb"),
        ("PYPL", "PayPal"),
        ("ARM", "Arm Holdings"),
        ("SMCI", "Super Micro Computer"),
        ("DELL", "Dell"),
        ("IBM", "IBM"),
        ("CSCO", "Cisco"),
    ],
    "Finanza": [
        ("JPM", "JPMorgan Chase"),
        ("BAC", "Bank of America"),
        ("WFC", "Wells Fargo"),
        ("C", "Citigroup"),
        ("GS", "Goldman Sachs"),
        ("MS", "Morgan Stanley"),
        ("BRK.B", "Berkshire Hathaway B"),
        ("V", "Visa"),
        ("MA", "Mastercard"),
        ("AXP", "American Express"),
        ("SCHW", "Charles Schwab"),
        ("BLK", "BlackRock"),
        ("HOOD", "Robinhood"),
        ("SOFI", "SoFi"),
    ],
    "Cripto (azioni ed ETF)": [
        ("IBIT", "iShares Bitcoin Trust"),
        ("ETHA", "iShares Ethereum Trust"),
        ("MSTR", "MicroStrategy"),
        ("COIN", "Coinbase"),
        ("MARA", "MARA Holdings"),
        ("RIOT", "Riot Platforms"),
    ],
    "Consumi e industria": [
        ("WMT", "Walmart"),
        ("COST", "Costco"),
        ("HD", "Home Depot"),
        ("NKE", "Nike"),
        ("SBUX", "Starbucks"),
        ("MCD", "McDonald's"),
        ("KO", "Coca-Cola"),
        ("PEP", "PepsiCo"),
        ("PG", "Procter & Gamble"),
        ("DIS", "Disney"),
        ("BA", "Boeing"),
        ("CAT", "Caterpillar"),
        ("GE", "GE Aerospace"),
        ("F", "Ford"),
        ("GM", "General Motors"),
        ("RIVN", "Rivian"),
        ("LMT", "Lockheed Martin"),
    ],
    "Sanità": [
        ("LLY", "Eli Lilly"),
        ("UNH", "UnitedHealth"),
        ("JNJ", "Johnson & Johnson"),
        ("PFE", "Pfizer"),
        ("MRK", "Merck"),
        ("ABBV", "AbbVie"),
        ("MRNA", "Moderna"),
        ("NVO", "Novo Nordisk (ADR)"),
    ],
    "Energia": [
        ("XOM", "ExxonMobil"),
        ("CVX", "Chevron"),
        ("OXY", "Occidental Petroleum"),
        ("COP", "ConocoPhillips"),
        ("SHEL", "Shell (ADR)"),
        ("BP", "BP (ADR)"),
    ],
    "Europa e Italia (quotate in USA)": [
        ("RACE", "Ferrari"),
        ("STLA", "Stellantis"),
        ("E", "Eni (ADR)"),
        ("ASML", "ASML"),
        ("SAP", "SAP"),
        ("NVO", "Novo Nordisk"),
        ("AZN", "AstraZeneca"),
        ("UL", "Unilever"),
        ("BABA", "Alibaba"),
        ("PDD", "PDD (Temu)"),
        ("NIO", "NIO"),
        ("SONY", "Sony"),
        ("TM", "Toyota"),
    ],
}

POPULAR = ["AAPL", "SPY", "QQQ", "TSLA", "NVDA", "_SPX", "RACE"]


# Indices listed on CBOE: they are requested with a leading underscore. Besides
# the catalogue ones, a few other common indices.
INDEX_ROOTS = {symbol.lstrip("_") for symbol, _ in CATALOG["Indici"]} | {
    "OEX",
    "XEO",
    "XND",
    "MRUT",
    "SPXW",
}

_PREFIXES = "_^$."


def display_symbol(symbol: str) -> str:
    """Symbol to display: upper case, without a leading ``_``, ``^`` or ``$``."""
    return symbol.strip().upper().lstrip(_PREFIXES)


def canonical_symbol(symbol: str) -> str:
    """Internal and CBOE spelling: ``_`` before indices, nothing for the rest."""
    plain = display_symbol(symbol)
    return f"_{plain}" if plain in INDEX_ROOTS else plain


def is_index(symbol: str) -> bool:
    return display_symbol(symbol) in INDEX_ROOTS


# Colour of each category in suggestions and buttons (see the tones in theme.py).
CATEGORY_TONES: dict[str, str] = {
    "Indici": "violet",
    "ETF di mercato": "blue",
    "ETF di settore": "teal",
    "Materie prime e obbligazioni": "amber",
    "Tecnologia": "blue",
    "Finanza": "green",
    "Cripto (azioni ed ETF)": "amber",
    "Consumi e industria": "red",
    "Sanità": "teal",
    "Energia": "red",
    "Europa e Italia (quotate in USA)": "violet",
}


def search(text: str, limit: int = 7) -> list[tuple[str, str, str]]:
    """Catalogue entries matching ``text``: (symbol, name, category).

    Order: exact symbol, symbol starting with it, name starting with it, name
    with another word starting with it, name containing it. So «ko» finds
    Coca-Cola (KO) first and then the rest. Names match in both languages.
    """
    query = display_symbol(text)
    if not query:
        return []
    ranked: dict[str, tuple[int, str, str, str]] = {}
    for category, items in CATALOG.items():
        for symbol, name in items:
            plain = display_symbol(symbol)
            shown = tr(name)
            upper_name = name.upper() if shown == name else f"{name.upper()} {shown.upper()}"
            if plain == query:
                rank = 0
            elif plain.startswith(query):
                rank = 1
            elif upper_name.startswith(query):
                rank = 2
            elif any(word.startswith(query) for word in upper_name.replace("(", " ").split()):
                rank = 3
            elif query in upper_name:
                rank = 4
            else:
                continue
            if symbol not in ranked or rank < ranked[symbol][0]:
                ranked[symbol] = (rank, symbol, shown, category)
    # Same relevance: shorter symbols for symbol searches, shorter names for
    # name searches («micro» -> Micron, Microsoft…).
    ordered = sorted(
        ranked.values(), key=lambda r: (r[0], len(r[1]) if r[0] < 2 else len(r[2]), r[1])
    )
    return [(symbol, name, category) for _, symbol, name, category in ordered[:limit]]


def company_name(symbol: str) -> str | None:
    """Company (or ETF, index) name if the symbol is in the catalogue."""
    wanted = canonical_symbol(symbol)
    for items in CATALOG.values():
        for candidate, name in items:
            if candidate == wanted:
                return tr(name)
    return None


def all_symbols() -> dict[str, str]:
    """Symbol -> «SYMBOL · name», for the search box. No duplicates."""
    options: dict[str, str] = {}
    for items in CATALOG.values():
        for symbol, name in items:
            options.setdefault(symbol, f"{display_symbol(symbol)} · {tr(name)}")
    return options
