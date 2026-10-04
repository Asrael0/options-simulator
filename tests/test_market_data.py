"""Interpretazione della catena CBOE e passaggio al simulatore (senza internet)."""

from __future__ import annotations

import math
from datetime import date

import pytest

from simulatore_opzioni_python.app.market_data import (
    BasketLeg,
    MarketDataError,
    model_vs_market,
    normalize_ticker,
    parse_chain,
    position_from_basket,
)
from simulatore_opzioni_python.pricing import ManualPremium, OptionLeg

TODAY = date(2026, 10, 3)


def _option(symbol: str, bid: float, ask: float, iv: float = 0.25) -> dict[str, object]:
    return {
        "option": symbol,
        "bid": bid,
        "ask": ask,
        "iv": iv,
        "delta": 0.5,
        "open_interest": 10.0,
        "volume": 1.0,
        "last_trade_price": 0.0,
    }


PAYLOAD = {
    "timestamp": "2026-10-03 03:44:04",
    "symbol": "AAPL",
    "data": {
        "symbol": "AAPL",
        "current_price": 100.0,
        "price_change_percent": 1.5,
        "iv30": 25.0,
        "options": [
            _option("AAPL261002C00100000", 1.0, 1.2),  # scaduta: va scartata
            _option("AAPL261016C00095000", 6.0, 6.4),
            _option("AAPL261016C00100000", 2.9, 3.1, iv=0.24),
            _option("AAPL261016P00100000", 2.5, 2.7, iv=0.26),
            _option("AAPL261016P00095000", 0.9, 1.1),
            _option("AAPL261016C00105000", 0.0, 0.0, iv=0.0),  # nessuna quotazione
            _option("SPXW261016C05000000", 1.0, 2.0),  # radice diversa, strike 5000
        ],
    },
}


def test_parse_chain_reads_symbols_and_drops_past_expiries() -> None:
    chain = parse_chain(PAYLOAD, TODAY)
    assert chain.ticker == "AAPL"
    assert chain.spot == 100.0
    assert chain.iv30 == pytest.approx(0.25)
    assert chain.change_pct == pytest.approx(0.015)
    assert chain.expiries == [date(2026, 10, 16)]
    assert chain.strikes(date(2026, 10, 16)) == [95.0, 100.0, 105.0, 5000.0]


def test_quote_mid_iv_and_atm_iv() -> None:
    chain = parse_chain(PAYLOAD, TODAY)
    expiry = date(2026, 10, 16)
    call = chain.quote(expiry, "call", 100.0)
    assert call is not None
    assert call.mid == pytest.approx(3.0)
    empty = chain.quote(expiry, "call", 105.0)
    assert empty is not None
    assert empty.mid is None
    assert empty.iv is None
    assert chain.atm_iv(expiry) == pytest.approx(0.25)  # media di 0.24 e 0.26


@pytest.mark.parametrize("payload", [{}, {"data": {"current_price": 0, "options": []}}])
def test_parse_chain_rejects_bad_payloads(payload: object) -> None:
    with pytest.raises(MarketDataError):
        parse_chain(payload, TODAY)


@pytest.mark.parametrize("bad", ["", "   ", "AAPL; rm", "X" * 11])
def test_normalize_ticker_rejects_garbage(bad: str) -> None:
    with pytest.raises(MarketDataError):
        normalize_ticker(bad)


def test_normalize_ticker_cleans_input() -> None:
    assert normalize_ticker("  spy ") == "SPY"
    assert normalize_ticker("_spx") == "_SPX"


def test_model_vs_market_satisfies_put_call_parity_for_european() -> None:
    chain = parse_chain(PAYLOAD, TODAY)
    expiry = date(2026, 10, 16)
    rows = model_vs_market(
        chain,
        expiry,
        iv=0.25,
        risk_free_rate=0.04,
        dividend_yield=0.0,
        exercise="european",
        today=TODAY,
    )
    assert [r.strike for r in rows] == chain.strikes(expiry)
    t = 13 / 365
    for row in rows:
        parity = chain.spot - row.strike * math.exp(-0.04 * t)
        assert row.call_model - row.put_model == pytest.approx(parity, abs=1e-6)
    atm = next(r for r in rows if r.strike == 100.0)
    assert atm.call_market == pytest.approx(3.0)
    assert atm.put_iv == pytest.approx(0.26)


def test_position_from_basket_uses_market_prices() -> None:
    chain = parse_chain(PAYLOAD, TODAY)
    expiry = date(2026, 10, 16)
    basket = [
        BasketLeg(right="call", side="long", strike=100.0, qty=1, premium=3.0, iv=0.24),
        BasketLeg(right="put", side="short", strike=95.0, qty=2, premium=1.0, iv=None),
    ]
    state = position_from_basket(chain, expiry, basket, risk_free_rate=0.045, today=TODAY)
    assert state.ticker == "AAPL"
    assert state.name == "Apple"
    assert state.market.spot == 100.0
    assert state.market.days_to_expiry == 13
    assert state.market.iv == pytest.approx(0.25)
    assert state.market.risk_free_rate == 0.045
    assert state.exercise == "american"
    first, second = state.legs
    assert isinstance(first, OptionLeg)
    assert isinstance(second, OptionLeg)
    assert first.premium == ManualPremium(3.0)
    assert (second.side, second.qty, second.strike) == ("short", 2, 95.0)
