"""Bora 0.8.0: project routing.yaml (resolution layer, generated-but-editable)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bora.routing import (
    ProjectRouting,
    RoutingConfigError,
    load_routing_file,
    write_routing_file,
)


def _init_project(root: Path, project_path: str = "Codebase/Target/Proj") -> Path:
    segments = project_path.split("/")
    d = root.joinpath("docs", "ai", *segments)
    d.mkdir(parents=True, exist_ok=True)
    return d


PROJECT = "Codebase/Target/Proj"


def test_round_trip_full_file(tmp_path):
    _init_project(tmp_path, PROJECT)
    routing = ProjectRouting(
        version=1,
        host="claude",
        synced="2026-08-25T14:30:00Z",
        source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": "claude-sonnet-4-6", "economy": None, "local": None},
        pinned=[],
        available=["claude-opus-4-6", "claude-sonnet-4-6"],
        unmatched_aliases={"economy": ["glm latest", "haiku"]},
    )
    write_routing_file(tmp_path, PROJECT, routing)

    loaded = load_routing_file(tmp_path, PROJECT)
    assert loaded is not None
    assert loaded.version == 1
    assert loaded.host == "claude"
    assert loaded.synced == "2026-08-25T14:30:00Z"
    assert loaded.source == "injected"
    assert loaded.tiers["premium"] == "claude-opus-4-6"
    assert loaded.tiers["economy"] is None
    assert loaded.available == ["claude-opus-4-6", "claude-sonnet-4-6"]
    assert loaded.unmatched_aliases == {"economy": ["glm latest", "haiku"]}


def test_missing_file_returns_none(tmp_path):
    _init_project(tmp_path, PROJECT)
    assert load_routing_file(tmp_path, PROJECT) is None


def test_wrong_version_raises(tmp_path):
    d = _init_project(tmp_path, PROJECT)
    (d / "routing.yaml").write_text("version: 2\ntiers: {}\n", encoding="utf-8")
    with pytest.raises(RoutingConfigError):
        load_routing_file(tmp_path, PROJECT)


def test_null_tier_values_are_valid(tmp_path):
    _init_project(tmp_path, PROJECT)
    routing = ProjectRouting(
        version=1, host="claude", synced=None, source=None,
        tiers={"premium": None, "standard": None, "economy": None, "local": None},
        pinned=[], available=[], unmatched_aliases={},
    )
    write_routing_file(tmp_path, PROJECT, routing)
    loaded = load_routing_file(tmp_path, PROJECT)
    assert loaded.tiers == {"premium": None, "standard": None, "economy": None, "local": None}


def test_unknown_tier_key_raises(tmp_path):
    d = _init_project(tmp_path, PROJECT)
    (d / "routing.yaml").write_text(
        "version: 1\ntiers:\n  bogus: something\n", encoding="utf-8"
    )
    with pytest.raises(RoutingConfigError):
        load_routing_file(tmp_path, PROJECT)


def test_empty_available_is_valid(tmp_path):
    _init_project(tmp_path, PROJECT)
    routing = ProjectRouting(
        version=1, host="claude", synced=None, source=None,
        tiers={"premium": None, "standard": None, "economy": None, "local": None},
        pinned=[], available=[], unmatched_aliases={},
    )
    write_routing_file(tmp_path, PROJECT, routing)
    loaded = load_routing_file(tmp_path, PROJECT)
    assert loaded.available == []


def test_unknown_pinned_tier_is_ignored_not_an_error(tmp_path):
    d = _init_project(tmp_path, PROJECT)
    (d / "routing.yaml").write_text(
        "version: 1\ntiers: {}\npinned: [bogus]\n", encoding="utf-8"
    )
    loaded = load_routing_file(tmp_path, PROJECT)
    assert loaded is not None
    assert loaded.pinned == []


def test_malformed_file_raises_naming_file(tmp_path):
    d = _init_project(tmp_path, PROJECT)
    (d / "routing.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
    with pytest.raises(RoutingConfigError, match="routing.yaml"):
        load_routing_file(tmp_path, PROJECT)


def test_pin_detection_on_hand_edit(tmp_path):
    _init_project(tmp_path, PROJECT)
    first = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": None, "economy": None, "local": None},
        pinned=[], available=["claude-opus-4-6"], unmatched_aliases={},
    )
    write_routing_file(tmp_path, PROJECT, first)

    # Simulate a user hand-editing premium to a different slug, then a
    # normal (non-repin) sync writing its own recomputed value.
    d = tmp_path.joinpath("docs", "ai", *PROJECT.split("/"))
    text = (d / "routing.yaml").read_text(encoding="utf-8")
    text = text.replace("claude-opus-4-6", "claude-opus-hand-edited", 1)
    (d / "routing.yaml").write_text(text, encoding="utf-8")

    second = ProjectRouting(
        version=1, host="claude", synced="t2", source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": "claude-sonnet-4-6", "economy": None, "local": None},
        pinned=[], available=["claude-opus-4-6", "claude-sonnet-4-6"], unmatched_aliases={},
    )
    result = write_routing_file(tmp_path, PROJECT, second)

    assert result.tiers["premium"] == "claude-opus-hand-edited"
    assert "premium" in result.pinned
    assert result.tiers["standard"] == "claude-sonnet-4-6"


def test_pinned_tier_survives_non_repin_write(tmp_path):
    _init_project(tmp_path, PROJECT)
    first = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "manual-pin", "standard": None, "economy": None, "local": None},
        pinned=["premium"], available=[], unmatched_aliases={},
    )
    write_routing_file(tmp_path, PROJECT, first)

    second = ProjectRouting(
        version=1, host="claude", synced="t2", source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": "claude-sonnet-4-6", "economy": None, "local": None},
        pinned=[], available=["claude-opus-4-6", "claude-sonnet-4-6"], unmatched_aliases={},
    )
    result = write_routing_file(tmp_path, PROJECT, second)

    assert result.tiers["premium"] == "manual-pin"
    assert "premium" in result.pinned
    assert result.tiers["standard"] == "claude-sonnet-4-6"


def test_repin_clears_pins_and_recomputes(tmp_path):
    _init_project(tmp_path, PROJECT)
    first = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "manual-pin", "standard": None, "economy": None, "local": None},
        pinned=["premium"], available=[], unmatched_aliases={},
    )
    write_routing_file(tmp_path, PROJECT, first)

    second = ProjectRouting(
        version=1, host="claude", synced="t2", source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": "claude-sonnet-4-6", "economy": None, "local": None},
        pinned=[], available=["claude-opus-4-6", "claude-sonnet-4-6"], unmatched_aliases={},
    )
    result = write_routing_file(tmp_path, PROJECT, second, repin=True)

    assert result.tiers["premium"] == "claude-opus-4-6"
    assert result.pinned == []
