"""Company names from the catalogue and expiry dates."""

from __future__ import annotations

from datetime import date

from options_simulator.app.formatting import expiry_date, format_expiry
from options_simulator.app.tickers import CATALOG, all_symbols, company_name


def test_company_name_from_catalog() -> None:
    assert company_name("AAPL") == "Apple"
    assert company_name(" race ") == "Ferrari"
    assert company_name("_SPX") == "S&P 500 (indice)"
    assert company_name("NONESISTE") is None


def test_catalog_has_no_duplicate_symbols_within_category() -> None:
    for items in CATALOG.values():
        symbols = [s for s, _ in items]
        assert len(symbols) == len(set(symbols))
    assert "AAPL" in all_symbols()


def test_expiry_date_formatting() -> None:
    today = date(2026, 10, 3)  # Saturday
    assert expiry_date(9, today) == date(2026, 10, 12)
    assert format_expiry(9, today) == "lun 12/10/2026"
    assert format_expiry(-5, today) == "sab 03/10/2026"


def test_search_ranks_symbol_matches_first() -> None:
    from options_simulator.app.tickers import search

    assert search("") == []
    assert search("ko")[0][0] == "KO"
    assert search("aapl")[0][:2] == ("AAPL", "Apple")
    assert search("spx")[0][0] == "_SPX"
    assert "RACE" in [symbol for symbol, _, _ in search("ferr")]
    assert len(search("a")) <= 7


def test_every_spelling_of_a_symbol_is_the_same() -> None:
    from options_simulator.app.carry import exercise_style
    from options_simulator.app.market_data import normalize_ticker
    from options_simulator.app.tickers import canonical_symbol, display_symbol, is_index

    for spelling in ["XSP", "xsp", "_XSP", "^XSP", " ^xsp "]:
        assert display_symbol(spelling) == "XSP"
        assert canonical_symbol(spelling) == "_XSP"
        assert normalize_ticker(spelling) == "_XSP"
        assert is_index(spelling)
        assert exercise_style(spelling) == "european"
        assert company_name(spelling) == "Mini S&P 500 (1/10 di SPX)"
    for spelling in ["aapl", "AAPL", "^AAPL"]:
        assert canonical_symbol(spelling) == "AAPL"
        assert exercise_style(spelling) == "american"


def test_search_finds_by_company_name() -> None:
    from options_simulator.app.tickers import search

    assert search("apple")[0][0] == "AAPL"
    assert search("bank of america")[0][0] == "BAC"
    assert search("^spx")[0][0] == "_SPX"


def test_chain_symbol_from_cboe_is_normalized() -> None:
    from options_simulator.app.market_data import parse_chain

    payload = {
        "symbol": "_XSP",
        "data": {
            "symbol": "^XSP",
            "current_price": 700.0,
            "options": [{"option": "XSP261016C00700000", "bid": 1.0, "ask": 1.2}],
        },
    }
    chain = parse_chain(payload, date(2026, 10, 3))
    assert chain.ticker == "_XSP"
