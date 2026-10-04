"""Scenario: P&L in un punto scelto e sua scomposizione."""

from __future__ import annotations

import pytest

from simulatore_opzioni_python.app.state import (
    MATRIX_IV_MOVES,
    MATRIX_PRICE_MOVES,
    PositionState,
    compute,
)


def test_neutral_scenario_equals_closing_today() -> None:
    state = PositionState()
    sc = compute(state).scenario
    assert sc.pl == pytest.approx(sc.pl_today)
    assert sc.effect_price == pytest.approx(0.0)
    assert sc.effect_time == pytest.approx(0.0)
    assert sc.effect_vol == pytest.approx(0.0)


@pytest.mark.parametrize("exercise", ["european", "american"])
def test_effects_add_up_to_scenario_pl(exercise: str) -> None:
    state = PositionState()
    state.apply_strategy("long_straddle")
    state.exercise = exercise  # type: ignore[assignment]
    state.target = 108.0
    state.days_forward = 12.0
    state.iv_sim = 0.18
    sc = compute(state).scenario
    total = sc.pl_today + sc.effect_price + sc.effect_time + sc.effect_vol
    assert sc.pl == pytest.approx(total, abs=1e-9)
    # Uno straddle comprato perde con il tempo e con il calo della IV.
    assert sc.effect_time < 0
    assert sc.effect_vol < 0
    assert sum(leg.pl for leg in sc.legs) == pytest.approx(sc.pl, abs=1e-9)


def test_matrix_shape_and_vol_crush_direction() -> None:
    state = PositionState()
    state.apply_strategy("long_straddle")
    sc = compute(state).scenario
    assert len(sc.matrix) == len(MATRIX_IV_MOVES)
    assert all(len(row) == len(MATRIX_PRICE_MOVES) for row in sc.matrix)
    centre = MATRIX_PRICE_MOVES.index(0.0)
    column = [row[centre] for row in sc.matrix]
    # Più IV, più vale uno straddle comprato: la colonna cresce dall'alto in basso.
    assert column == sorted(column)


def test_scenario_price_follows_spot_until_moved() -> None:
    state = PositionState()
    state.set_market(spot=120.0)
    assert state.target == 120.0
    state.target = 130.0
    state.set_market(spot=125.0)
    assert state.target == 130.0
