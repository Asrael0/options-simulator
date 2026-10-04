"""Catalogo dei titoli proposti nella pagina «Opzioni reali».

--- COSA FA QUESTO FILE ---
Solo un elenco: simbolo, nome e categoria di circa 150 titoli, ETF e indici
con opzioni molto scambiate su CBOE. Serve alla casella di ricerca e ai
pulsanti per categoria.

Non è un limite: qualunque simbolo USA con opzioni funziona anche se non è qui,
basta scriverlo.

UN SIMBOLO, UNA SCRITTURA. CBOE scrive gli indici in tre modi: si chiedono come
``_SPX``, nelle opzioni compaiono come ``SPX`` e nella risposta tornano come
``^SPX``. Qui c'è l'unica regola del programma:
  - ``canonical_symbol`` dà la forma interna, quella da chiedere a CBOE
    (``_SPX`` per gli indici, ``AAPL`` per il resto);
  - ``display_symbol`` dà la forma da mostrare, sempre pulita (``SPX``).
Qualunque cosa scriva l'utente (``spx``, ``_SPX``, ``^SPX``) diventa la stessa.
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


# Indici quotati su CBOE: vanno chiesti con il trattino basso davanti. Oltre a
# quelli del catalogo, qualche altro indice comune.
INDEX_ROOTS = {symbol.lstrip("_") for symbol, _ in CATALOG["Indici"]} | {
    "OEX",
    "XEO",
    "XND",
    "MRUT",
    "SPXW",
}

_PREFIXES = "_^$."


def display_symbol(symbol: str) -> str:
    """Simbolo da mostrare: maiuscolo e senza ``_``, ``^`` o ``$`` davanti."""
    return symbol.strip().upper().lstrip(_PREFIXES)


def canonical_symbol(symbol: str) -> str:
    """Forma interna e per CBOE: ``_`` davanti agli indici, nulla per il resto."""
    plain = display_symbol(symbol)
    return f"_{plain}" if plain in INDEX_ROOTS else plain


def is_index(symbol: str) -> bool:
    return display_symbol(symbol) in INDEX_ROOTS


# Colore di ogni categoria nei suggerimenti e nei pulsanti (vedi i toni in theme.py).
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
    """Titoli del catalogo che corrispondono a ``text``: (simbolo, nome, categoria).

    Ordine: simbolo identico, simbolo che inizia così, nome che inizia così,
    nome con un'altra parola che inizia così, nome che contiene il testo.
    Così «ko» trova prima Coca-Cola (KO) e poi il resto.
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
    # A parità di pertinenza: simboli più corti per chi cerca un simbolo,
    # nomi più corti per chi cerca un nome («micro» -> Micron, Microsoft…).
    ordered = sorted(
        ranked.values(), key=lambda r: (r[0], len(r[1]) if r[0] < 2 else len(r[2]), r[1])
    )
    return [(symbol, name, category) for _, symbol, name, category in ordered[:limit]]


def company_name(symbol: str) -> str | None:
    """Nome dell'azienda (o dell'ETF, dell'indice) se il simbolo è nel catalogo."""
    wanted = canonical_symbol(symbol)
    for items in CATALOG.values():
        for candidate, name in items:
            if candidate == wanted:
                return tr(name)
    return None


def all_symbols() -> dict[str, str]:
    """Simbolo -> «SIMBOLO · nome», per la casella di ricerca. Senza doppioni."""
    options: dict[str, str] = {}
    for items in CATALOG.values():
        for symbol, name in items:
            options.setdefault(symbol, f"{display_symbol(symbol)} · {tr(name)}")
    return options
