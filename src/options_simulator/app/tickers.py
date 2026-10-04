"""Catalogue of the stocks suggested on the «Real options» page.

Just a list: symbol, name and category of about 300 stocks, ETFs and indices
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
        ("IVV", "iShares Core S&P 500"),
        ("VTI", "Vanguard Total Stock Market"),
        ("RSP", "Invesco S&P 500 Equal Weight"),
        ("MDY", "SPDR S&P MidCap 400"),
        ("IJR", "iShares Core S&P Small-Cap"),
        ("VGK", "Vanguard FTSE Europe"),
        ("EWU", "iShares Regno Unito"),
        ("EWC", "iShares Canada"),
        ("EWA", "iShares Australia"),
        ("EWY", "iShares Corea del Sud"),
        ("EWT", "iShares Taiwan"),
        ("INDA", "iShares India"),
        ("MCHI", "iShares Cina"),
        ("KWEB", "KraneShares China Internet"),
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
        ("XLC", "Servizi di comunicazione"),
        ("XLB", "Materiali"),
        ("XLRE", "Immobiliare"),
        ("XOP", "Petrolio e gas, esplorazione"),
        ("XRT", "Commercio al dettaglio"),
        ("XHB", "Costruttori di case"),
        ("ITB", "iShares Costruzioni residenziali"),
        ("IBB", "iShares Biotecnologie"),
        ("SOXX", "iShares Semiconduttori"),
        ("JETS", "Compagnie aeree"),
        ("TAN", "Energia solare"),
        ("URA", "Uranio"),
    ],
    "ETF a leva e volatilità": [
        ("TQQQ", "ProShares UltraPro QQQ (3x)"),
        ("SQQQ", "ProShares UltraPro Short QQQ (−3x)"),
        ("SPXL", "Direxion S&P 500 Bull (3x)"),
        ("SOXL", "Direxion Semiconduttori Bull (3x)"),
        ("UVXY", "ProShares Ultra VIX a breve"),
        ("VXX", "iPath VIX a breve"),
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
        ("IAU", "iShares Oro"),
        ("GDXJ", "Minatori d'oro junior"),
        ("SIL", "Minatori d'argento"),
        ("COPX", "Minatori di rame"),
        ("DBA", "Agricoltura"),
        ("SHY", "Treasury USA 1-3 anni"),
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
        ("CRWD", "CrowdStrike"),
        ("PANW", "Palo Alto Networks"),
        ("NOW", "ServiceNow"),
        ("INTU", "Intuit"),
        ("TXN", "Texas Instruments"),
        ("MRVL", "Marvell Technology"),
        ("LRCX", "Lam Research"),
        ("AMAT", "Applied Materials"),
        ("KLAC", "KLA"),
        ("ON", "ON Semiconductor"),
        ("NET", "Cloudflare"),
        ("DDOG", "Datadog"),
        ("ZS", "Zscaler"),
        ("MDB", "MongoDB"),
        ("WDAY", "Workday"),
        ("SNPS", "Synopsys"),
        ("CDNS", "Cadence Design Systems"),
        ("ANET", "Arista Networks"),
        ("APP", "AppLovin"),
        ("RBLX", "Roblox"),
        ("ZM", "Zoom"),
        ("SPOT", "Spotify"),
        ("TTD", "The Trade Desk"),
        ("PINS", "Pinterest"),
        ("SNAP", "Snap"),
        ("RDDT", "Reddit"),
        ("HPQ", "HP"),
        ("HPE", "Hewlett Packard Enterprise"),
        ("WDC", "Western Digital"),
        ("STX", "Seagate"),
        ("DASH", "DoorDash"),
        ("LYFT", "Lyft"),
        ("ROKU", "Roku"),
        ("TTWO", "Take-Two Interactive"),
        ("CRWV", "CoreWeave"),
        ("PATH", "UiPath"),
        ("AI", "C3.ai"),
    ],
    "Spazio e nuove tecnologie": [
        ("SPCX", "SpaceX"),
        ("RKLB", "Rocket Lab"),
        ("ASTS", "AST SpaceMobile"),
        ("IONQ", "IonQ"),
        ("RGTI", "Rigetti Computing"),
        ("SOUN", "SoundHound AI"),
        ("OKLO", "Oklo"),
        ("SMR", "NuScale Power"),
        ("JOBY", "Joby Aviation"),
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
        ("USB", "U.S. Bancorp"),
        ("COF", "Capital One"),
        ("BX", "Blackstone"),
        ("KKR", "KKR"),
        ("SPGI", "S&P Global"),
        ("CME", "CME Group"),
        ("ICE", "Intercontinental Exchange"),
        ("MET", "MetLife"),
        ("AIG", "AIG"),
        ("AFRM", "Affirm"),
        ("UPST", "Upstart"),
        ("NU", "Nu Holdings"),
        ("XYZ", "Block"),
    ],
    "Cripto (azioni ed ETF)": [
        ("IBIT", "iShares Bitcoin Trust"),
        ("ETHA", "iShares Ethereum Trust"),
        ("MSTR", "MicroStrategy"),
        ("COIN", "Coinbase"),
        ("MARA", "MARA Holdings"),
        ("RIOT", "Riot Platforms"),
        ("FBTC", "Fidelity Wise Origin Bitcoin"),
        ("GBTC", "Grayscale Bitcoin Trust"),
        ("BITO", "ProShares Bitcoin Strategy"),
        ("CLSK", "CleanSpark"),
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
        ("TGT", "Target"),
        ("LOW", "Lowe's"),
        ("CMG", "Chipotle"),
        ("LULU", "Lululemon"),
        ("DE", "Deere"),
        ("HON", "Honeywell"),
        ("UPS", "UPS"),
        ("FDX", "FedEx"),
        ("RTX", "RTX"),
        ("NOC", "Northrop Grumman"),
        ("GD", "General Dynamics"),
        ("UNP", "Union Pacific"),
        ("DAL", "Delta Air Lines"),
        ("UAL", "United Airlines"),
        ("AAL", "American Airlines"),
        ("CCL", "Carnival"),
        ("RCL", "Royal Caribbean"),
        ("MAR", "Marriott"),
        ("BKNG", "Booking Holdings"),
        ("EBAY", "eBay"),
        ("ETSY", "Etsy"),
        ("CVNA", "Carvana"),
        ("CHWY", "Chewy"),
        ("GME", "GameStop"),
        ("AMC", "AMC Entertainment"),
        ("LCID", "Lucid"),
        ("MMM", "3M"),
        ("PM", "Philip Morris"),
        ("MO", "Altria"),
        ("MDLZ", "Mondelez"),
        ("CL", "Colgate-Palmolive"),
        ("TJX", "TJX"),
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
        ("AMGN", "Amgen"),
        ("GILD", "Gilead Sciences"),
        ("BMY", "Bristol-Myers Squibb"),
        ("CVS", "CVS Health"),
        ("ISRG", "Intuitive Surgical"),
        ("TMO", "Thermo Fisher"),
        ("ABT", "Abbott"),
        ("MDT", "Medtronic"),
        ("VRTX", "Vertex Pharmaceuticals"),
        ("REGN", "Regeneron"),
        ("HIMS", "Hims & Hers"),
    ],
    "Energia": [
        ("XOM", "ExxonMobil"),
        ("CVX", "Chevron"),
        ("OXY", "Occidental Petroleum"),
        ("COP", "ConocoPhillips"),
        ("SHEL", "Shell (ADR)"),
        ("BP", "BP (ADR)"),
        ("SLB", "SLB (Schlumberger)"),
        ("HAL", "Halliburton"),
        ("EOG", "EOG Resources"),
        ("DVN", "Devon Energy"),
        ("MPC", "Marathon Petroleum"),
        ("VLO", "Valero"),
        ("PSX", "Phillips 66"),
        ("KMI", "Kinder Morgan"),
        ("FSLR", "First Solar"),
        ("ENPH", "Enphase Energy"),
        ("NEE", "NextEra Energy"),
        ("VST", "Vistra"),
        ("CEG", "Constellation Energy"),
        ("CCJ", "Cameco"),
    ],
    "Estero e Italia (quotate in USA)": [
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
        ("STM", "STMicroelectronics"),
        ("TS", "Tenaris"),
        ("CNH", "CNH Industrial"),
        ("TTE", "TotalEnergies"),
        ("GSK", "GSK"),
        ("NVS", "Novartis"),
        ("BTI", "British American Tobacco"),
        ("DEO", "Diageo"),
        ("RIO", "Rio Tinto"),
        ("BHP", "BHP"),
        ("HSBC", "HSBC"),
        ("UBS", "UBS"),
        ("DB", "Deutsche Bank"),
        ("SAN", "Banco Santander"),
        ("BIDU", "Baidu"),
        ("JD", "JD.com"),
        ("XPEV", "XPeng"),
        ("LI", "Li Auto"),
        ("SE", "Sea Limited"),
        ("MELI", "MercadoLibre"),
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
    "Estero e Italia (quotate in USA)": "violet",
    "ETF a leva e volatilità": "amber",
    "Spazio e nuove tecnologie": "violet",
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
