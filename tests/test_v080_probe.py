"""Bora 0.8.0: endpoint probe (the only permitted network path) + socket guard."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from bora.cli import main
from bora.probe import ProbeError, probe_models, strip_userinfo


# --- probe_models (pure, injected transport) --------------------------------

def _openai_transport(data):
    def transport(url, headers, timeout):
        if url.endswith("/v1/models"):
            return 200, json.dumps({"data": data}).encode("utf-8")
        return 404, b"not found"

    return transport


def _ollama_transport(models):
    def transport(url, headers, timeout):
        if url.endswith("/v1/models"):
            return 404, b"not found"
        if url.endswith("/api/tags"):
            return 200, json.dumps({"models": models}).encode("utf-8")
        return 404, b"not found"

    return transport


def test_probe_openai_shape_returns_ids():
    transport = _openai_transport([{"id": "a"}, {"id": "b"}])
    result = probe_models("http://localhost:1234", transport=transport)
    assert result == ["a", "b"]


def test_probe_falls_through_to_ollama_shape():
    transport = _ollama_transport([{"name": "llama3"}])
    result = probe_models("http://localhost:11434", transport=transport)
    assert result == ["llama3"]


def test_probe_sends_bearer_token_when_given():
    seen_headers = {}

    def transport(url, headers, timeout):
        seen_headers.update(headers)
        return 200, json.dumps({"data": [{"id": "a"}]}).encode("utf-8")

    probe_models("http://localhost:1234", token="secret-token", transport=transport)
    assert seen_headers.get("Authorization") == "Bearer secret-token"


def test_probe_no_auth_header_when_no_token():
    seen_headers = {}

    def transport(url, headers, timeout):
        seen_headers.update(headers)
        return 200, json.dumps({"data": [{"id": "a"}]}).encode("utf-8")

    probe_models("http://localhost:1234", transport=transport)
    assert "Authorization" not in seen_headers


def test_probe_connection_failure_aborts_without_second_shape():
    calls = []

    def transport(url, headers, timeout):
        calls.append(url)
        raise ProbeError(f"Could not reach {url}")

    with pytest.raises(ProbeError):
        probe_models("http://localhost:1234", transport=transport)
    assert len(calls) == 1


def test_probe_both_shapes_fail_raises_naming_url():
    def transport(url, headers, timeout):
        return 404, b"not found"

    with pytest.raises(ProbeError, match="localhost:1234"):
        probe_models("http://localhost:1234", transport=transport)


def test_probe_unparseable_body_raises():
    def transport(url, headers, timeout):
        return 200, b"not json at all"

    with pytest.raises(ProbeError):
        probe_models("http://localhost:1234", transport=transport)


def test_probe_timeout_passed_to_transport():
    seen = {}

    def transport(url, headers, timeout):
        seen["timeout"] = timeout
        return 200, json.dumps({"data": [{"id": "a"}]}).encode("utf-8")

    probe_models("http://localhost:1234", transport=transport)
    assert seen["timeout"] == 10.0


def test_strip_userinfo_removes_credentials():
    assert strip_userinfo("http://user:pass@localhost:1234") == "http://localhost:1234"


def test_strip_userinfo_no_userinfo_unchanged():
    assert strip_userinfo("http://localhost:1234") == "http://localhost:1234"


# --- CLI --probe wiring -------------------------------------------------

SAMPLE = "QromaCore/Hamburg/Gallery Refactor"

CATALOG_YAML = """\
routing:
  enabled: true
  tiers:
    premium:
      - opus
    standard:
      - sonnet
    economy:
      - glm latest
    local:
      - ollama-model
"""


def _runner():
    return CliRunner()


def _init_synced_project(runner, td):
    runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
    path = Path(td) / ".bora" / "models.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CATALOG_YAML, encoding="utf-8")
    return Path(td) / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "routing.yaml"


def _refusing_transport(*_a, **_kw):
    raise AssertionError("transport must not be called")


def test_probe_key_env_missing_errors_before_any_request(monkeypatch):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        _init_synced_project(runner, td)
        monkeypatch.delenv("MISSING_PROBE_KEY", raising=False)
        monkeypatch.setattr("bora.cli.probe_models", _refusing_transport)
        result = runner.invoke(
            main,
            [
                "dev", "routing", "sync", SAMPLE,
                "--host", "local-ollama",
                "--probe", "http://localhost:11434",
                "--probe-key-env", "MISSING_PROBE_KEY",
            ],
        )
        assert result.exit_code != 0
        assert "MISSING_PROBE_KEY" in result.output


def test_probe_credential_never_appears_in_output_or_file(monkeypatch):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        monkeypatch.setenv("PROBE_KEY", "super-secret-value")

        seen_kwargs = {}

        def fake_probe_models(base_url, **kwargs):
            seen_kwargs.update(kwargs)
            return ["claude-opus-4-6"]

        monkeypatch.setattr("bora.cli.probe_models", fake_probe_models)
        result = runner.invoke(
            main,
            [
                "dev", "routing", "sync", SAMPLE,
                "--host", "local-ollama",
                "--probe", "http://localhost:11434",
                "--probe-key-env", "PROBE_KEY",
            ],
        )
        assert result.exit_code == 0, result.output
        assert seen_kwargs.get("token") == "super-secret-value"
        assert "super-secret-value" not in result.output
        assert "super-secret-value" not in routing_path.read_text(encoding="utf-8")


def test_probe_source_recorded_with_userinfo_stripped(monkeypatch):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        monkeypatch.setattr("bora.cli.probe_models", lambda base_url, **kw: ["claude-opus-4-6"])
        result = runner.invoke(
            main,
            [
                "dev", "routing", "sync", SAMPLE,
                "--host", "local-ollama",
                "--probe", "http://user:pass@localhost:11434",
            ],
        )
        assert result.exit_code == 0, result.output
        data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
        assert data["source"] == "probe:http://localhost:11434"
        assert "user:pass" not in routing_path.read_text(encoding="utf-8")


def test_sync_neither_available_nor_probe_is_usage_error():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        _init_synced_project(runner, td)
        result = runner.invoke(main, ["dev", "routing", "sync", SAMPLE, "--host", "claude"])
        assert result.exit_code != 0


def test_sync_both_available_and_probe_is_usage_error():
    runner = _runner()
    with runner.isolated_filesystem() as td:
        _init_synced_project(runner, td)
        avail = Path(td) / "available.txt"
        avail.write_text("claude-opus-4-6\n", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "dev", "routing", "sync", SAMPLE,
                "--host", "claude",
                "--available", str(avail),
                "--probe", "http://localhost:11434",
            ],
        )
        assert result.exit_code != 0


def test_probe_error_writes_no_partial_file(monkeypatch):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        routing_path = _init_synced_project(runner, td)
        before = routing_path.read_bytes()

        def raising(*a, **kw):
            raise ProbeError("Could not reach http://localhost:11434: connection refused")

        monkeypatch.setattr("bora.cli.probe_models", raising)
        result = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "local-ollama", "--probe", "http://localhost:11434"],
        )
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert routing_path.read_bytes() == before


# --- Socket guard: every non-probe path stays offline -----------------------

class _SocketGuardTripped(Exception):
    pass


def _guarded_connect(*_a, **_kw):
    raise _SocketGuardTripped("network I/O attempted outside an explicit --probe call")


@pytest.fixture
def no_sockets(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    yield


def test_init_status_lint_never_touch_the_network(no_sockets):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        Path(td, ".bora", "models.yaml").parent.mkdir(parents=True, exist_ok=True)
        Path(td, ".bora", "models.yaml").write_text(CATALOG_YAML, encoding="utf-8")
        r1 = runner.invoke(main, ["dev", "status", SAMPLE])
        r2 = runner.invoke(main, ["dev", "lint", SAMPLE])
        r3 = runner.invoke(main, ["dev", "routing", "show", SAMPLE])
        for r in (r1, r2, r3):
            assert not isinstance(r.exception, _SocketGuardTripped), r.output


def test_routing_resolve_and_sync_available_never_touch_the_network(no_sockets):
    runner = _runner()
    with runner.isolated_filesystem() as td:
        runner.invoke(main, ["dev", "init", SAMPLE, "--routing"])
        Path(td, ".bora", "models.yaml").parent.mkdir(parents=True, exist_ok=True)
        Path(td, ".bora", "models.yaml").write_text(CATALOG_YAML, encoding="utf-8")
        avail = Path(td) / "available.txt"
        avail.write_text("claude-opus-4-6\nclaude-sonnet-4-6\n", encoding="utf-8")
        r1 = runner.invoke(
            main,
            ["dev", "routing", "resolve", SAMPLE, "--host", "claude", "--available", str(avail)],
        )
        r2 = runner.invoke(
            main,
            ["dev", "routing", "sync", SAMPLE, "--host", "claude", "--available", str(avail)],
        )
        for r in (r1, r2):
            assert not isinstance(r.exception, _SocketGuardTripped), r.output
