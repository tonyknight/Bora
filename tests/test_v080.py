"""Bora 0.8.0: project routing.yaml (resolution layer, generated-but-editable)."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
import yaml

from bora.routing import (
    ProjectRouting,
    RoutingConfigError,
    load_routing_file,
    write_routing_file,
)


def _guarded_connect(*_a, **_kw):
    raise AssertionError(
        "network I/O attempted in tests/test_v080.py — this module covers "
        "routing.yaml, init, and routing sync --available, none of which "
        "should ever open a socket"
    )


@pytest.fixture(autouse=True)
def _no_sockets(monkeypatch):
    """Every test in this file must stay offline (ticket 04, Requirements §10)."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    yield


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


# --- Init stub + docs/ai/ path rejection (ticket 02) -----------------------

from click.testing import CliRunner

from bora.cli import main

SAMPLE = "QromaCore/Hamburg/Gallery Refactor"


def _runner():
    return CliRunner()


def test_init_docs_ai_prefix_rejected_names_corrected_path():
    runner = _runner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", "docs/ai/Bora/v0.8.0"])
        assert result.exit_code != 0
        assert "Bora/v0.8.0" in result.output


def test_init_dot_slash_docs_ai_prefix_rejected():
    runner = _runner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", "./docs/ai/Bora/v0.8.0"])
        assert result.exit_code != 0
        assert "Bora/v0.8.0" in result.output


def test_init_backslash_docs_ai_prefix_rejected():
    runner = _runner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", "docs\\ai\\Bora\\v0.8.0"])
        assert result.exit_code != 0
        assert "Bora/v0.8.0" in result.output


def test_status_rejects_docs_ai_prefix():
    runner = _runner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        result = runner.invoke(main, ["dev", "status", "docs/ai/Bora/v0.8.0"])
        assert result.exit_code != 0
        assert "Bora/v0.8.0" in result.output


def test_lint_rejects_docs_ai_prefix():
    runner = _runner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        result = runner.invoke(main, ["dev", "lint", "docs/ai/Bora/v0.8.0"])
        assert result.exit_code != 0
        assert "Bora/v0.8.0" in result.output


def test_normal_path_unaffected_by_prefix_rejection():
    runner = _runner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        assert result.exit_code == 0, result.output


def test_init_routing_writes_stub_routing_yaml():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert result.exit_code == 0, result.output
        stub = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"
        assert stub.exists()
        text = stub.read_text(encoding="utf-8")
        assert "version: 1" in text
        assert "bora dev routing sync" in text
        for tier in ("premium", "standard", "economy", "local"):
            assert f"{tier}: null" in text or f"{tier}:\n" in text
        assert "available: []" in text
        assert "Created" in result.output
        assert "routing.yaml" in result.output


def test_init_no_routing_writes_no_stub():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        assert result.exit_code == 0, result.output
        stub = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"
        assert not stub.exists()


def test_init_missing_catalog_still_writes_stub_and_note():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert result.exit_code == 0, result.output
        stub = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"
        assert stub.exists()
        assert ".bora/models.yaml" in result.output


# --- routing sync --available (ticket 03) -----------------------------------

def _write_models_yaml_v080(root: Path, text: str) -> Path:
    path = root / ".bora" / "models.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


CATALOG_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - opus
      - grok latest high
    standard:
      - sonnet
    economy:
      - glm latest
      - haiku
      - gpt-5-nano
    local:
      - ollama
"""


def _init_synced_project(runner, td):
    runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
    _write_models_yaml_v080(Path(td), CATALOG_YAML)
    return Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"


def _available_file(td, lines):
    p = Path(td) / "available.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_sync_unique_match_resolves_tiers():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available)],
        )
        assert result.exit_code == 0, result.output
        text = routing_path.read_text(encoding="utf-8")
        assert "claude-opus-4-6" in text
        assert "claude-sonnet-4-6" in text


def test_sync_zero_matches_writes_full_inventory_no_prompt():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available = _available_file(td, ["totally-unrelated-model-a", "totally-unrelated-model-b"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available)],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
        assert data["tiers"]["premium"] is None
        assert data["tiers"]["standard"] is None
        assert set(data["available"]) == {"totally-unrelated-model-a", "totally-unrelated-model-b"}


def test_sync_ambiguous_alias_leaves_tier_null_with_unmatched_aliases():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        # "glm latest" / "haiku" / "gpt-5-nano" all fail to match; two models
        # both substring-match "claude opus" ambiguously for premium.
        available = _available_file(td, ["claude-opus-a", "claude-opus-b", "claude-sonnet-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available)],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
        assert data["tiers"]["premium"] is None
        assert "premium" in data["unmatched_aliases"]


def test_sync_dry_run_writes_nothing():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        before = routing_path.read_bytes()
        available = _available_file(td, ["claude-opus-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available), "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert routing_path.read_bytes() == before


def test_sync_missing_catalog_errors_no_file_written():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        routing_path = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"
        before = routing_path.read_bytes()
        available = _available_file(td, ["claude-opus-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available)],
        )
        assert result.exit_code != 0
        assert routing_path.read_bytes() == before


def test_sync_not_opted_in_errors():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        _write_models_yaml_v080(Path(td), CATALOG_YAML)
        available = _available_file(td, ["claude-opus-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available)],
        )
        assert result.exit_code != 0


def test_sync_preserves_pinned_tier():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available1 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available1)],
        )
        # Hand-edit premium.
        text = routing_path.read_text(encoding="utf-8")
        text = text.replace("claude-opus-4-6", "hand-picked-model", 1)
        routing_path.write_text(text, encoding="utf-8")

        available2 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6", "hand-picked-model"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available2)],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
        assert data["tiers"]["premium"] == "hand-picked-model"
        assert "premium" in data["pinned"]


def test_sync_warns_when_pinned_slug_no_longer_available():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available1 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available1)],
        )
        text = routing_path.read_text(encoding="utf-8")
        text = text.replace("claude-opus-4-6", "hand-picked-model", 1)
        routing_path.write_text(text, encoding="utf-8")

        # Second sync: hand-picked-model is gone from the available set.
        available2 = _available_file(td, ["claude-sonnet-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available2)],
        )
        assert result.exit_code == 0, result.output
        assert "premium" in result.output
        assert "hand-picked-model" in result.output


def test_sync_repin_clears_pin_and_states_discard():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available1 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available1)],
        )
        text = routing_path.read_text(encoding="utf-8")
        text = text.replace("claude-opus-4-6", "hand-picked-model", 1)
        routing_path.write_text(text, encoding="utf-8")

        available2 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6", "hand-picked-model"])
        # A normal sync first records the hand-edit as an actual pin.
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available2)],
        )
        assert "premium" in yaml.safe_load(routing_path.read_text(encoding="utf-8"))["pinned"]

        available3 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available3), "--repin"],
        )
        assert result.exit_code == 0, result.output
        assert "premium" in result.output
        data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
        assert data["tiers"]["premium"] == "claude-opus-4-6"
        assert data["pinned"] == []


def test_sync_missing_available_file_is_usage_error():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        _init_synced_project(runner, td)
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(Path(td) / "nope.txt")],
        )
        assert result.exit_code != 0


# --- Session resolve precedence + routing show (ticket 05) ------------------

from bora.routing import MATCH_MATCHED, resolve_session


def test_resolve_session_prefers_routing_yaml_over_catalog_match():
    routing_yaml = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "hand-picked-model", "standard": None, "economy": None, "local": None},
        pinned=["premium"], available=["claude-opus-4-6"], unmatched_aliases={},
    )
    tiers = {"premium": ["opus"]}
    available = ["claude-opus-4-6", "hand-picked-model"]
    session = resolve_session(tiers, available, host="claude", routing_yaml=routing_yaml)
    assert session["premium"].status == MATCH_MATCHED
    assert session["premium"].slug == "hand-picked-model"


def test_resolve_session_unpinned_routing_yaml_entry_also_wins():
    routing_yaml = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "claude-opus-4-6", "standard": None, "economy": None, "local": None},
        pinned=[], available=["claude-opus-4-6"], unmatched_aliases={},
    )
    tiers = {"premium": ["opus"]}
    available = ["claude-opus-4-6"]
    session = resolve_session(tiers, available, host="claude", routing_yaml=routing_yaml)
    assert session["premium"].status == MATCH_MATCHED
    assert session["premium"].slug == "claude-opus-4-6"


def test_resolve_session_stale_routing_yaml_slug_falls_back_to_catalog():
    routing_yaml = ProjectRouting(
        version=1, host="claude", synced="t1", source="injected",
        tiers={"premium": "vanished-model", "standard": None, "economy": None, "local": None},
        pinned=["premium"], available=[], unmatched_aliases={},
    )
    tiers = {"premium": ["opus"]}
    available = ["claude-opus-4-6"]
    session = resolve_session(tiers, available, host="claude", routing_yaml=routing_yaml)
    assert session["premium"].status == MATCH_MATCHED
    assert session["premium"].slug == "claude-opus-4-6"
    assert session["premium"].stale_routing_slug == "vanished-model"


def test_resolve_session_no_routing_yaml_unchanged_075_behavior():
    tiers = {"premium": ["opus"]}
    available = ["claude-opus-4-6"]
    session = resolve_session(tiers, available, host="claude", routing_yaml=None)
    assert session["premium"].status == MATCH_MATCHED
    assert session["premium"].slug == "claude-opus-4-6"
    assert session["premium"].stale_routing_slug is None


def test_resolve_session_cursor_cache_still_ignored_for_claude_host():
    tiers = {"premium": ["opus"]}
    available = ["claude-opus-4-6", "claude-opus-4-5"]
    cache = {"cursor": {"premium": "grok-4-6"}}
    session = resolve_session(tiers, available, host="claude", cache=cache, routing_yaml=None)
    # "opus" is ambiguous between the two claude-opus models; cursor's cache
    # must not leak into a claude-host suggestion.
    assert session["premium"].suggest is None


def test_routing_resolve_cli_uses_routing_yaml_and_reports_stale():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available1 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available1)],
        )
        text = routing_path.read_text(encoding="utf-8")
        text = text.replace("claude-opus-4-6", "vanished-model", 1)
        routing_path.write_text(text, encoding="utf-8")

        available2 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        result = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "claude", "--available", str(available2)],
        )
        assert result.exit_code == 0, result.output
        assert "vanished-model" in result.output
        assert "claude-opus-4-6" in result.output
        # Read-only: routing.yaml on disk is untouched by resolve.
        assert "vanished-model" in routing_path.read_text(encoding="utf-8")


def test_routing_show_reports_no_routing_file():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Project routing file: none" in result.output


def test_routing_show_reports_synced_routing_file_with_pinned_marker():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        available1 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available1)],
        )
        text = routing_path.read_text(encoding="utf-8")
        text = text.replace("claude-opus-4-6", "hand-picked-model", 1)
        routing_path.write_text(text, encoding="utf-8")
        available2 = _available_file(td, ["claude-opus-4-6", "claude-sonnet-4-6", "hand-picked-model"])
        runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(available2)],
        )

        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Project routing file:" in result.output
        assert "hand-picked-model" in result.output
        assert "[pinned]" in result.output


# --- Ticket completion fragments (ticket 06) ---------------------------------

def test_ticket_new_includes_completion_report_section():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        result = runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "Some ticket", "--no-edit"])
        assert result.exit_code == 0, result.output
        tickets_dir = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets"
        files = [p for p in tickets_dir.glob("*.md") if p.name != ".gitkeep"]
        assert len(files) == 1
        text = files[0].read_text(encoding="utf-8")
        assert "## Completion report" in text
        assert "**Outcome:**" in text
        assert "**Files:**" in text
        assert "**Errors:**" in text
        assert "**Verify:**" in text


def _ticket_path(td, name):
    return Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets" / name


def test_lint_errors_on_done_ticket_with_empty_completion_report():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "Some ticket", "--no-edit"])
        tickets_dir = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets"
        path = next(p for p in tickets_dir.glob("*.md") if p.name != ".gitkeep")
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: todo", "status: done").replace("closed:\n", "closed: 2026-08-25\n", 1)
        path.write_text(text, encoding="utf-8")

        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code != 0
        assert "Completion report" in result.output


def test_lint_passes_on_done_ticket_with_filled_completion_report():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "Some ticket", "--no-edit"])
        tickets_dir = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets"
        path = next(p for p in tickets_dir.glob("*.md") if p.name != ".gitkeep")
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: todo", "status: done").replace("closed:\n", "closed: 2026-08-25\n", 1)
        text = text.replace("- **Outcome:**", "- **Outcome:** did the thing")
        text = text.replace("- **Files:**", "- **Files:** bora/foo.py")
        text = text.replace("- **Errors:**", "- **Errors:** none")
        text = text.replace("- **Verify:**", "- **Verify:** pytest — 5 passed")
        path.write_text(text, encoding="utf-8")

        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 0, result.output


def test_lint_warns_not_errors_on_legacy_done_ticket_without_section():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "Some ticket", "--no-edit"])
        tickets_dir = Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets"
        path = next(p for p in tickets_dir.glob("*.md") if p.name != ".gitkeep")
        text = path.read_text(encoding="utf-8")
        text = text.replace("status: todo", "status: done").replace("closed:\n", "closed: 2026-08-25\n", 1)
        # Strip the whole Completion report section to simulate a pre-0.8.0 ticket.
        start = text.index("## Completion report")
        end = text.index("## Notes")
        text = text[:start] + text[end:]
        path.write_text(text, encoding="utf-8")

        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Completion report" in result.output
        assert "warning" in result.output.lower()


def test_lint_ignores_empty_completion_report_on_non_done_ticket():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        runner.invoke(main, ["dev", "ticket", "new", SAMPLE, "Some ticket", "--no-edit"])
        result = runner.invoke(main, ["dev", "lint", SAMPLE])
        assert result.exit_code == 0, result.output
