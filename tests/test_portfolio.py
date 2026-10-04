"""Portafoglio virtuale: apertura, valutazione, chiusura, scadenza."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from options_simulator.app import auth, portfolio
from options_simulator.app.market_data import BasketLeg, Chain, parse_chain

TODAY = date(2026, 10, 3)
EXPIRY = date(2026, 10, 16)


def _chain(spot: float, call_100: tuple[float, float], call_110: tuple[float, float]) -> Chain:
    """Catena minima: due call sulla stessa scadenza, con denaro e lettera dati."""
    payload = {
        "symbol": "AAPL",
        "data": {
            "symbol": "AAPL",
            "current_price": spot,
            "iv30": 25.0,
            "options": [
                {
                    "option": "AAPL261016C00100000",
                    "bid": call_100[0],
                    "ask": call_100[1],
                    "iv": 0.25,
                },
                {"option": "AAPL261016P00100000", "bid": 2.0, "ask": 2.2, "iv": 0.25},
                {
                    "option": "AAPL261016C00110000",
                    "bid": call_110[0],
                    "ask": call_110[1],
                    "iv": 0.24,
                },
            ],
        },
    }
    return parse_chain(payload, TODAY)


SPREAD = [
    BasketLeg(right="call", side="long", strike=100.0, qty=2, premium=3.1, iv=0.25),
    BasketLeg(right="call", side="short", strike=110.0, qty=2, premium=0.8, iv=0.24),
]


@pytest.fixture
def user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(auth, "DATA_DIR", tmp_path)
    return "anna"


def _open(user: str) -> portfolio.PaperPosition:
    chain = _chain(100.0, (2.9, 3.1), (0.8, 1.0))
    return portfolio.open_position(
        user,
        chain,
        EXPIRY,
        SPREAD,
        rate=0.045,
        dividend=0.0,
        exercise="american",
        note="sale",
        today=TODAY,
    )


def test_open_records_real_prices_and_forecast(user: str) -> None:
    position = _open(user)
    # Debito: (3,10 - 0,80) per 2 contratti per 100 azioni.
    assert position.entry_cost == pytest.approx(460.0)
    assert position.name == "Apple"
    assert position.note == "sale"
    assert 0.0 < position.forecast.prob_profit < 1.0
    assert position.forecast.max_loss == pytest.approx(-460.0, abs=1e-6)
    assert position.forecast.max_profit == pytest.approx(10 * 200 - 460.0, abs=1e-6)
    # Valutata subito al mid: (3,00 - 0,90) per 200 = 420: perde lo spread.
    assert position.last_value == pytest.approx(420.0)
    assert position.pl == pytest.approx(-40.0)
    assert portfolio.list_for(user)[0].position_id == position.position_id


def test_refresh_adds_one_snapshot_per_day(user: str) -> None:
    position = _open(user)
    later = _chain(106.0, (7.0, 7.2), (1.9, 2.1))
    assert portfolio.refresh(user, {"AAPL": later}, TODAY) == 1
    assert portfolio.refresh(user, {"AAPL": later}, TODAY) == 1
    updated = portfolio.list_for(user)[0]
    assert len(updated.snapshots) == 1  # stesso giorno: sostituito, non aggiunto
    assert updated.last_value == pytest.approx((7.1 - 2.0) * 200)
    assert updated.pl == pytest.approx((7.1 - 2.0) * 200 - position.entry_cost)
    assert updated.last_spot == 106.0


def test_close_uses_bid_for_longs_and_ask_for_shorts(user: str) -> None:
    position = _open(user)
    later = _chain(106.0, (7.0, 7.2), (1.9, 2.1))
    closed = portfolio.close_position(user, position.position_id, later, TODAY)
    assert closed.status == "closed"
    # Vendo la call 100 al denaro (7,00), ricompro la 110 alla lettera (2,10).
    assert closed.exit_value == pytest.approx((7.0 - 2.1) * 200)
    assert closed.pl == pytest.approx((7.0 - 2.1) * 200 - 460.0)


def test_expired_position_settles_at_intrinsic(user: str) -> None:
    _open(user)
    after_expiry = date(2026, 10, 17)
    portfolio.refresh(user, {"AAPL": _chain(104.0, (0.0, 0.0), (0.0, 0.0))}, after_expiry)
    settled = portfolio.list_for(user)[0]
    assert settled.status == "closed"
    assert settled.settled_at_expiry
    assert settled.exit_value == pytest.approx(4.0 * 200)


def test_calibration_compares_forecast_with_outcome(user: str) -> None:
    first = _open(user)
    second = _open(user)
    portfolio.close_position(user, first.position_id, _chain(106.0, (7.0, 7.2), (1.9, 2.1)), TODAY)
    portfolio.close_position(user, second.position_id, _chain(95.0, (0.5, 0.7), (0.05, 0.1)), TODAY)
    result = portfolio.calibration(portfolio.list_for(user))
    assert result is not None
    assert (result.closed, result.wins) == (2, 1)
    assert result.win_rate == 0.5
    assert result.average_probability == pytest.approx(first.forecast.prob_profit)


def test_delete_and_empty_basket(user: str) -> None:
    position = _open(user)
    portfolio.delete(user, position.position_id)
    assert portfolio.list_for(user) == []
    with pytest.raises(ValueError):
        portfolio.open_position(
            user,
            _chain(100.0, (2.9, 3.1), (0.8, 1.0)),
            EXPIRY,
            [],
            rate=0.04,
            dividend=0.0,
            exercise="american",
            today=TODAY,
        )
