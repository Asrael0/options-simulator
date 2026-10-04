"""Saving and reopening positions."""

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
    assert saved.save("anna", "Test", state) is None
    state.set_market(spot=150.0)
    assert saved.save("anna", "Test", state) is None  # same name: updates

    items = saved.list_for("anna")
    assert len(items) == 1
    assert items[0].data["market"]["spot"] == 150.0
    assert saved.list_for("bruno") == []

    saved.delete("anna", items[0].position_id)
    assert saved.list_for("anna") == []


def test_export_import_roundtrip() -> None:
    original = _custom_state()
    name, restored = saved.import_bytes(saved.export_bytes("Mine", original))
    assert name == "Mine"
    assert saved.to_dict(restored) == saved.to_dict(original)


@pytest.mark.parametrize("content", [b"not json", b"{}", b'{"format": "other"}'])
def test_import_rejects_foreign_files(content: bytes) -> None:
    with pytest.raises(ValueError):
        saved.import_bytes(content)


def test_import_accepts_files_exported_by_older_versions() -> None:
    import json

    current = json.loads(saved.export_bytes("Old", _custom_state()))
    legacy = {
        "formato": "simulatore-opzioni",
        "versione": 1,
        "nome": "Old",
        "posizione": current["position"],
    }
    name, restored = saved.import_bytes(json.dumps(legacy).encode("utf-8"))
    assert name == "Old"
    assert saved.to_dict(restored) == current["position"]


def test_legacy_data_dir_is_moved_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old, new = tmp_path / ".simulatore-opzioni", tmp_path / ".options-simulator"
    old.mkdir()
    (old / "users.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auth, "LEGACY_DATA_DIR", old)
    monkeypatch.setattr(auth, "DATA_DIR", new)
    auth.migrate_legacy_data_dir()
    assert (new / "users.json").exists()
    assert not old.exists()
    auth.migrate_legacy_data_dir()  # the second time nothing happens
    assert (new / "users.json").exists()


def test_legacy_file_names_are_renamed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "LEGACY_DATA_DIR", tmp_path / "missing")
    monkeypatch.setattr(auth, "DATA_DIR", tmp_path)
    (tmp_path / "posizioni.json").write_text("{}", encoding="utf-8")
    (tmp_path / "portfolio.json").write_text('{"new": []}', encoding="utf-8")
    (tmp_path / "portafoglio.json").write_text('{"old": []}', encoding="utf-8")
    auth.migrate_legacy_data_dir()
    assert (tmp_path / "positions.json").exists()
    assert not (tmp_path / "posizioni.json").exists()
    # An existing new file is never overwritten.
    assert (tmp_path / "portfolio.json").read_text(encoding="utf-8") == '{"new": []}'
