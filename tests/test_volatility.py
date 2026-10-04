"""Volatilità storica e confronto con l'implicita (senza internet)."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from simulatore_opzioni_python.app.market_data import MarketDataError
from simulatore_opzioni_python.app.volatility import (
    PricePoint,
    build_report,
    history_symbol,
    parse_history,
    realized_volatility,
    rolling_volatility,
    verdict_for,
)


def _zigzag(days: int, step: float, start: float = 100.0) -> list[PricePoint]:
    """Prezzi che salgono e scendono dello stesso rendimento logaritmico ogni giorno."""
    points = []
    price = start
    for i in range(days):
        points.append(PricePoint(date(2025, 1, 1) + timedelta(days=i), price))
        price *= math.exp(step if i % 2 == 0 else -step)
    return points


def test_realized_volatility_of_known_series() -> None:
    closes = [p.close for p in _zigzag(300, 0.01)]
    # Rendimenti ±1% al giorno: deviazione standard 1%, annualizzata x √252.
    expected = 0.01 * math.sqrt(252)
    for window in (20, 60, 252):
        assert realized_volatility(closes, window) == pytest.approx(expected, rel=0.03)


def test_constant_prices_have_zero_volatility() -> None:
    assert realized_volatility([50.0] * 40, 20) == pytest.approx(0.0)


def test_rolling_volatility_follows_regime_change() -> None:
    calm = _zigzag(200, 0.005)
    wild = _zigzag(120, 0.03, start=calm[-1].close)
    points = calm + [
        PricePoint(calm[-1].day + timedelta(days=i + 1), p.close) for i, p in enumerate(wild)
    ]
    series = rolling_volatility(points, window=30)
    assert series[0][1] < 0.15
    assert series[-1][1] > 0.40


@pytest.mark.parametrize(
    ("ratio", "verdict"),
    [(1.6, "care"), (1.25, "care"), (1.1, "nella media"), (0.9, "economiche"), (None, None)],
)
def test_verdict_thresholds(ratio: float | None, verdict: str | None) -> None:
    assert verdict_for(ratio) == verdict


def test_report_compares_iv_with_history() -> None:
    points = _zigzag(400, 0.01)
    hv = 0.01 * math.sqrt(252)
    expensive = build_report(points, iv=hv * 1.5, source="TEST")
    assert expensive.verdict == "care"
    assert expensive.percentile == pytest.approx(1.0)
    cheap = build_report(points, iv=hv * 0.7, source="TEST")
    assert cheap.verdict == "economiche"
    assert cheap.percentile == pytest.approx(0.0)
    assert len(expensive.prices) == 252


def test_short_history_is_rejected() -> None:
    with pytest.raises(MarketDataError):
        build_report(_zigzag(10, 0.01), iv=0.2, source="TEST")


def test_history_symbol_uses_etf_for_indices() -> None:
    assert history_symbol("AAPL") == "AAPL"
    assert history_symbol("_SPX") == "SPY"
    assert history_symbol("^XSP") == "SPY"
    assert history_symbol("NDX") == "QQQ"
    assert history_symbol("VIX") is None


def test_parse_history_sorts_and_skips_empty_rows() -> None:
    payload = {
        "data": [
            {"date": "2026-10-02", "close": 101.0},
            {"date": "2026-10-01", "close": 100.0},
            {"date": "2026-09-30", "close": None},
        ]
    }
    points = parse_history(payload)
    assert [p.close for p in points] == [100.0, 101.0]
    with pytest.raises(MarketDataError):
        parse_history({"niente": []})
