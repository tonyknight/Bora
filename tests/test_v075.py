"""Bora 0.7.5: ordered catalog lists, opt-in, session resolve."""

from __future__ import annotations

from pathlib import Path

import pytest

from bora.routing import (
    DEFAULT_SKILL_TIERS,
    RoutingConfigError,
    load_models_config,
    resolve_effective_routing,
)


def _write_models_yaml(root: Path, text: str) -> Path:
    path = root / ".bora" / "models.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


LIST_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - grok latest high
      - claude opus
      - gpt-5
    standard:
      - composer
      - sonnet
      - gpt-5-mini
    economy:
      - glm latest
      - haiku
      - gpt-5-nano
    local:
      - ollama
  skills:
    bora-review: economy
"""

CSV_YAML = """\
routing:
  enabled: true
  tiers:
    premium: "grok latest high, claude opus, gpt-5"
    standard: composer, sonnet, gpt-5-mini
    economy: " glm latest , haiku , gpt-5-nano "
    local: ollama
"""

SCALAR_YAML = """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
    standard: auto/coding
    economy: auto/cheap
    local: auto/offline
"""

FIVE_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - a
      - b
      - c
      - d
      - e
    standard: one
    economy: two
    local: three
"""


def test_yaml_list_parses_in_order(tmp_path):
    _write_models_yaml(tmp_path, LIST_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is True
    assert resolved.tiers["premium"] == [
        "grok latest high",
        "claude opus",
        "gpt-5",
    ]
    assert resolved.tiers["standard"] == ["composer", "sonnet", "gpt-5-mini"]
    assert resolved.tiers["economy"] == ["glm latest", "haiku", "gpt-5-nano"]
    assert resolved.tiers["local"] == ["ollama"]
    assert resolved.skill_tiers["bora-review"] == "economy"


def test_csv_string_splits_and_strips(tmp_path):
    _write_models_yaml(tmp_path, CSV_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == [
        "grok latest high",
        "claude opus",
        "gpt-5",
    ]
    assert resolved.tiers["standard"] == ["composer", "sonnet", "gpt-5-mini"]
    assert resolved.tiers["economy"] == ["glm latest", "haiku", "gpt-5-nano"]
    assert resolved.tiers["local"] == ["ollama"]


def test_scalar_string_becomes_one_item_list(tmp_path):
    _write_models_yaml(tmp_path, SCALAR_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == ["auto/smart"]
    assert resolved.tiers["standard"] == ["auto/coding"]
    assert resolved.tiers["economy"] == ["auto/cheap"]
    assert resolved.tiers["local"] == ["auto/offline"]


def test_empty_yaml_sequence_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: []
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_empty_string_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: "   "
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_csv_empty_tokens_only_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: ", , ,"
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


def test_five_aliases_allowed(tmp_path):
    _write_models_yaml(tmp_path, FIVE_YAML)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.tiers["premium"] == ["a", "b", "c", "d", "e"]


def test_missing_models_yaml_is_disabled_not_error(tmp_path):
    load_models_config(tmp_path)
    resolved = resolve_effective_routing(tmp_path)
    assert resolved.enabled is False
    assert resolved.tiers == {}
    assert resolved.skill_tiers == DEFAULT_SKILL_TIERS


def test_unknown_skill_override_raises(tmp_path):
    _write_models_yaml(
        tmp_path,
        """\
routing:
  enabled: true
  tiers:
    premium: auto/smart
  skills:
    not-a-bora-skill: economy
""",
    )
    with pytest.raises(RoutingConfigError):
        load_models_config(tmp_path)


# ---------------------------------------------------------------------------
# Project opt-in and init
# ---------------------------------------------------------------------------

from click.testing import CliRunner

from bora.cli import main
from bora.paths import project_file
from bora.routing import briefing_frontmatter, project_is_routing_opted_in

SAMPLE = "Acme/Auth"


def test_briefing_without_routing_is_not_opted_in():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 0, result.output
        root = Path(".")
        assert project_is_routing_opted_in(root, SAMPLE) is False
        fm = briefing_frontmatter(root, SAMPLE)
        assert "routing" not in fm


def test_routing_true_is_opted_in():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 0, result.output
        path = project_file(Path("."), SAMPLE)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("---\n", "---\nrouting: true\n", 1), encoding="utf-8")
        assert project_is_routing_opted_in(Path("."), SAMPLE) is True


def test_init_no_routing_and_non_tty_do_not_opt_in():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
        assert result.exit_code == 0, result.output
        assert project_is_routing_opted_in(Path("."), SAMPLE) is False
        assert "routing: true" not in project_file(Path("."), SAMPLE).read_text(
            encoding="utf-8"
        )
        assert not Path(".bora/models.yaml").exists()


def test_init_routing_flag_writes_opt_in_not_models_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert result.exit_code == 0, result.output
        assert project_is_routing_opted_in(Path("."), SAMPLE) is True
        text = project_file(Path("."), SAMPLE).read_text(encoding="utf-8")
        assert "routing: true" in text
        assert not Path(".bora/models.yaml").exists()
        combined = result.output.lower()
        assert "models.yaml" in combined or "alias" in combined


def test_init_tty_prompt_default_no(monkeypatch):
    monkeypatch.setattr("bora.cli._stdin_is_tty", lambda: True)
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE], input="\n")
        assert result.exit_code == 0, result.output
        assert "Use cost-efficiency routing for this project?" in result.output
        assert project_is_routing_opted_in(Path("."), SAMPLE) is False


def test_malformed_routing_cache_is_ignored():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["dev", "init", SAMPLE])
        assert result.exit_code == 0, result.output
        path = project_file(Path("."), SAMPLE)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("---\n", "---\nrouting: true\nrouting_cache: not-a-map\n", 1),
            encoding="utf-8",
        )
        from bora.routing import routing_cache_for_host

        cache = routing_cache_for_host(
            briefing_frontmatter(Path("."), SAMPLE), "cursor"
        )
        assert cache == {}


# ---------------------------------------------------------------------------
# Session matcher
# ---------------------------------------------------------------------------

from bora.routing import MATCH_ASK, MATCH_MATCHED, match_tier, resolve_session


def test_first_unique_alias_wins():
    result = match_tier(
        ["grok latest high", "claude opus", "gpt-5"],
        ["composer-2", "grok-4-6", "gpt-5-mini"],
    )
    assert result.status == MATCH_MATCHED
    assert result.slug == "grok-4-6"


def test_ambiguous_alias_asks():
    result = match_tier(
        ["sonnet"],
        ["claude-sonnet-4-6", "claude-sonnet-4-5"],
    )
    assert result.status == MATCH_ASK
    assert result.slug is None
    assert "claude-sonnet-4-6" in result.candidates
    assert "claude-sonnet-4-5" in result.candidates


def test_no_alias_match_asks():
    result = match_tier(["grok latest high"], ["composer-2", "gpt-5-mini"])
    assert result.status == MATCH_ASK
    assert result.slug is None
    assert result.candidates == []


def test_cursor_cache_ignored_for_claude_host():
    aliases = {"premium": ["opus"]}
    available = ["claude-opus-4-6"]
    cache = {"cursor": {"premium": "grok-4-6"}}
    session = resolve_session(aliases, available, host="claude", cache=cache)
    assert session["premium"].status == MATCH_MATCHED
    assert session["premium"].slug == "claude-opus-4-6"
    assert session["premium"].suggest is None


def test_unique_match_overrides_stale_cache():
    result = match_tier(
        ["composer"],
        ["composer-2", "glm-4.6"],
        cache_slug="glm-4.6",
    )
    assert result.status == MATCH_MATCHED
    assert result.slug == "composer-2"


def test_failed_match_suggests_still_available_cache():
    result = match_tier(
        ["grok latest high"],
        ["composer-2", "glm-4.6"],
        cache_slug="glm-4.6",
    )
    assert result.status == MATCH_ASK
    assert result.slug is None
    assert result.suggest == "glm-4.6"


def test_match_tier_makes_no_network_calls(monkeypatch):
    import socket
    import urllib.request

    def _fail(*_args, **_kwargs):
        pytest.fail("unexpected network I/O")

    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    monkeypatch.setattr(socket, "create_connection", _fail)
    match_tier(["composer"], ["composer-2"])
    resolve_session({"standard": ["composer"]}, ["composer-2"], host="cursor", cache={})


# ---------------------------------------------------------------------------
# CLI show + resolve
# ---------------------------------------------------------------------------


def test_routing_show_lists_and_opt_in():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert init.exit_code == 0, init.output
        _write_models_yaml(Path("."), LIST_YAML)
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Status: enabled" in result.output
        assert "Project opt-in: yes" in result.output
        assert "grok latest high, claude opus, gpt-5" in result.output
        assert "composer, sonnet, gpt-5-mini" in result.output


def test_routing_show_opt_in_no_without_flag():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        result = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Project opt-in: no" in result.output


def test_routing_resolve_missing_available_file():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert init.exit_code == 0, init.output
        _write_models_yaml(Path("."), LIST_YAML)
        result = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "cursor", "--available", "missing.txt"],
        )
        assert result.exit_code != 0
        combined = (result.output or "") + (result.stderr or "")
        assert "not found" in combined.lower()


def test_routing_resolve_requires_opt_in_and_catalog():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        Path("models.txt").write_text("composer-2\n", encoding="utf-8")
        missing = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "cursor", "--available", "models.txt"],
        )
        assert missing.exit_code != 0
        _write_models_yaml(Path("."), LIST_YAML)
        not_opted = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "cursor", "--available", "models.txt"],
        )
        assert not_opted.exit_code != 0
        combined = (not_opted.output or "") + (not_opted.stderr or "")
        assert "opted" in combined.lower()


def test_routing_resolve_is_read_only_and_prints_match():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        assert init.exit_code == 0, init.output
        _write_models_yaml(Path("."), LIST_YAML)
        briefing = project_file(Path("."), SAMPLE)
        before = briefing.read_bytes()
        Path("models.txt").write_text(
            "grok-4-6\ncomposer-2\nhaiku-4-5\nollama\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "cursor", "--available", "models.txt"],
        )
        assert result.exit_code == 0, result.output
        assert "grok-4-6" in result.output
        assert "composer-2" in result.output
        assert briefing.read_bytes() == before


def test_version_is_075():
    from bora import __version__
    from bora.profile import CURRENT_VERSION
    from bora.templates import AGENTS_TEMPLATE_VERSION

    assert __version__ == "0.7.5"
    assert CURRENT_VERSION == "0.7.5"
    assert AGENTS_TEMPLATE_VERSION == "0.7.5"


def test_bora_and_execute_document_session_resolve():
    from bora.skill_pack import render_pack_skill

    bora = render_pack_skill("bora").lower()
    execute = render_pack_skill("bora-execute").lower()
    for text in (bora, execute):
        assert "routing: true" in text
        assert "routing resolve" in text
        assert "ask" in text
        assert "routing_cache" in text
        assert "does not choose models" in text


def test_upgrade_does_not_add_routing_opt_in():
    runner = CliRunner()
    with runner.isolated_filesystem():
        init = runner.invoke(main, ["dev", "init", SAMPLE])
        assert init.exit_code == 0, init.output
        briefing = project_file(Path("."), SAMPLE)
        before = briefing.read_bytes()
        install = runner.invoke(main, ["dev", "skill", "install", "cursor", "--project"])
        assert install.exit_code == 0, install.output
        upgrade = runner.invoke(main, ["dev", "upgrade"])
        assert upgrade.exit_code == 0, upgrade.output
        assert briefing.read_bytes() == before
        assert "routing: true" not in briefing.read_text(encoding="utf-8")
        assert not Path(".bora/models.yaml").exists()


def test_readme_covers_lists_opt_in_and_resolve():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "routing: true" in readme
    assert "routing resolve" in readme
    assert "Cursor" in readme and "Claude Code" in readme
    assert "OmniRoute" in readme
    start = readme.find("## Quick start (dev)")
    end = readme.find("## Workflow cycle")
    quickstart = readme[start:end]
    assert "models.yaml" not in quickstart
