"""Salvataggio e riapertura delle posizioni."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from options_simulator.app import auth, saved
from options_simulator.app.state import PositionState
from options_simulator.pricing import ManualPremium, OptionLeg, Sizing, StockLeg


def _custom_state() -> PositionState:
    state = PositionState()
    state.add_leg()
    first = state.legs[0]
    assert isinstance(first, OptionLeg)
    state.legs[0] = replace(first, premium=ManualPremium(4.2), strike=105.0)
    state.legs.append(StockLeg(leg_id="s1", side="short", qty=2.0, entry_price=98.5))
    state.set_market(spot=101.0, iv=0.42)
    state.exercise = "american"
    state.sizing = Sizing(contract_multiplier=10.0, packages=3)
    state.target = 120.0
    return state


def test_roundtrip_keeps_everything_but_ids() -> None:
    original = _custom_state()
    restored = saved.from_dict(saved.to_dict(original))
    assert saved.to_dict(restored) == saved.to_dict(original)
    assert restored.market == original.market
    first = restored.legs[0]
    assert isinstance(first, OptionLeg)
    assert first.premium == ManualPremium(4.2)


def test_broken_data_raises_value_error() -> None:
    with pytest.raises(ValueError):
        saved.from_dict({"legs": []})


def test_save_list_overwrite_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "DATA_DIR", tmp_path)
    state = PositionState()

    assert saved.save("anna", "  ", state) is not None
    assert saved.save("anna", "Prova", state) is None
    state.set_market(spot=150.0)
    assert saved.save("anna", "Prova", state) is None  # stesso nome: aggiorna

    items = saved.list_for("anna")
    assert len(items) == 1
    assert items[0].data["market"]["spot"] == 150.0
    assert saved.list_for("bruno") == []

    saved.delete("anna", items[0].position_id)
    assert saved.list_for("anna") == []


def test_export_import_roundtrip() -> None:
    original = _custom_state()
    name, restored = saved.import_bytes(saved.export_bytes("Mia", original))
    assert name == "Mia"
    assert saved.to_dict(restored) == saved.to_dict(original)


@pytest.mark.parametrize("content", [b"non json", b"{}", b'{"formato": "altro"}'])
def test_import_rejects_foreign_files(content: bytes) -> None:
    with pytest.raises(ValueError):
        saved.import_bytes(content)


def test_import_accepts_files_exported_with_the_old_name() -> None:
    import json

    payload = json.loads(saved.export_bytes("Vecchia", _custom_state()))
    payload["formato"] = "simulatore-opzioni"
    name, _ = saved.import_bytes(json.dumps(payload).encode("utf-8"))
    assert name == "Vecchia"


def test_legacy_data_dir_is_moved_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = tmp_path / ".simulatore-opzioni", tmp_path / ".options-simulator"
    old.mkdir()
    (old / "users.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auth, "LEGACY_DATA_DIR", old)
    monkeypatch.setattr(auth, "DATA_DIR", new)
    auth.migrate_legacy_data_dir()
    assert (new / "users.json").exists()
    assert not old.exists()
    auth.migrate_legacy_data_dir()  # la seconda volta non succede nulla
    assert (new / "users.json").exists()
