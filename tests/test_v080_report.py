"""Bora 0.8.0: assemble a project's Completion document from ticket fragments."""

from __future__ import annotations

import os
import subprocess
import socket
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from bora.cli import main
from bora.report import build_completion_report


def _guarded_connect(*_a, **_kw):
    raise AssertionError("network I/O attempted in tests/test_v080_report.py")


@pytest.fixture(autouse=True)
def _no_sockets(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    yield


@pytest.fixture(autouse=True)
def _restore_cwd():
    """`_init_git_project` chdirs into a temp root for CliRunner calls that
    resolve `Path.cwd()` themselves (dev init, ticket new); restore the real
    cwd after each test so this never leaks into other test files."""
    original = os.getcwd()
    yield
    os.chdir(original)


SAMPLE = "QromaCore/Hamburg/Gallery Refactor"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _commit_file(root: Path, relpath: str, content: str, message: str) -> str:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(root, "add", relpath)
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _init_git_project(td: str) -> Path:
    root = Path(td)
    os.chdir(root)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    runner = CliRunner()
    result = runner.invoke(main, ["dev", "init", SAMPLE, "--no-routing"])
    assert result.exit_code == 0, result.output
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _write_requirements(root: Path):
    reqs_dir = root / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor"
    reqs_path = next(reqs_dir.glob("*Requirements.md"))
    text = reqs_path.read_text(encoding="utf-8")
    text = text.replace(
        "## Non-goals\n\n## Architecture",
        "## Non-goals\n\n- Deferred: fancy dashboards\n- Deferred: multi-tenant support\n\n## Architecture",
    )
    text = text.replace(
        "## Testing requirements\n\nName the project verify command(s) here",
        "## Testing requirements\n\nNamed command: **`pytest`**.\n\nOld text you can ignore: Name the project verify command(s) here",
    )
    reqs_path.write_text(text, encoding="utf-8")


def _new_ticket(root: Path, title: str) -> Path:
    runner = CliRunner()
    result = runner.invoke(main, ["dev", "ticket", "new", SAMPLE, title, "--no-edit"])
    assert result.exit_code == 0, result.output
    tickets_dir = root / "docs" / "ai" / "QromaCore" / "Hamburg" / "Gallery Refactor" / "tickets"
    files = sorted(p for p in tickets_dir.glob("*.md") if p.name != ".gitkeep")
    return files[-1]


def _fill_completion_report(path: Path, *, outcome: str, files: str, errors: str, verify: str):
    text = path.read_text(encoding="utf-8")
    text = text.replace("status: todo", "status: done")
    text = text.replace("closed:\n", "closed: 2026-08-25\n", 1)
    text = text.replace("- **Outcome:**", f"- **Outcome:** {outcome}")
    text = text.replace("- **Files:**", f"- **Files:** {files}")
    text = text.replace("- **Errors:**", f"- **Errors:** {errors}")
    text = text.replace("- **Verify:**", f"- **Verify:** {verify}")
    path.write_text(text, encoding="utf-8")


def _append_review_range(path: Path, start: str, end: str):
    text = path.read_text(encoding="utf-8")
    text += f"\n\n## Review\n\n- Range: `{start}..{end}`\n"
    path.write_text(text, encoding="utf-8")


def test_report_build_front_matter_and_header(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")

    assert "status: complete" in text
    assert f"last_reviewed: {date.today().isoformat()}" in text
    assert "origin_branch:" in text
    assert "execute_branch:" in text
    assert "pytest" in text


def test_report_build_sections_in_ticket_id_order(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)

    t1 = _new_ticket(root, "First ticket")
    t2 = _new_ticket(root, "Second ticket")
    _fill_completion_report(t1, outcome="did A", files="a.py", errors="none", verify="pytest — 1 passed")
    _fill_completion_report(t2, outcome="did B", files="b.py", errors="none", verify="pytest — 2 passed")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")

    assert text.index("did A") < text.index("did B")
    assert "First ticket" in text
    assert "Second ticket" in text


def test_report_build_git_reconciliation_no_mismatch(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Real change")

    sha1 = _commit_file(root, "src/thing.py", "print('t01')\n", "ticket T01")
    sha2 = _commit_file(root, "src/thing.py", "print('t02')\n", "ticket T02")

    _fill_completion_report(t1, outcome="changed thing", files="src/thing.py", errors="none", verify="pytest — 1 passed")
    _append_review_range(t1, sha1, sha2)

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "src/thing.py" in text
    assert "mismatch" not in text.lower()


def test_report_build_git_reconciliation_flags_mismatch(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Wrong files claim")

    sha1 = _commit_file(root, "src/real.py", "print('t01')\n", "ticket T01")
    sha2 = _commit_file(root, "src/real.py", "print('t02')\n", "ticket T02")

    _fill_completion_report(t1, outcome="changed real", files="src/wrong.py", errors="none", verify="pytest — 1 passed")
    _append_review_range(t1, sha1, sha2)

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "mismatch" in text.lower()
    assert "src/real.py" in text


def test_report_build_no_review_range_falls_back_to_prose(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "No range ticket")
    _fill_completion_report(t1, outcome="did it", files="c.py", errors="none", verify="pytest — 1 passed")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "c.py" in text


def test_report_build_legacy_ticket_without_fragment_shows_not_recorded(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Legacy ticket")
    text = t1.read_text(encoding="utf-8")
    # Simulate a pre-0.8.0 ticket: strip the Completion report section entirely.
    start = text.index("## Completion report")
    end = text.index("## Notes")
    text = text[:start] + text[end:]
    text = text.replace("status: todo", "status: done").replace("closed:\n", "closed: 2026-08-25\n", 1)
    t1.write_text(text, encoding="utf-8")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "not recorded" in text.lower()


def test_report_build_errors_and_deviations_section(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Had an error")
    t2 = _new_ticket(root, "Clean ticket")
    _fill_completion_report(t1, outcome="x", files="x.py", errors="flaky test retried once", verify="pytest — 1 passed")
    _fill_completion_report(t2, outcome="y", files="y.py", errors="none", verify="pytest — 1 passed")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "Errors and deviations" in text
    assert "flaky test retried once" in text


def test_report_build_testing_guide_from_acceptance_criteria(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Feature ticket")
    text = t1.read_text(encoding="utf-8")
    text = text.replace(
        "- [ ] Concrete, checkable condition\n- [ ] Another concrete condition",
        "- [ ] Widget spins when clicked\n- [ ] Widget stops when clicked again",
    )
    t1.write_text(text, encoding="utf-8")
    _fill_completion_report(t1, outcome="built widget", files="widget.py", errors="none", verify="pytest — 1 passed")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "Testing guide" in text
    assert "Widget spins when clicked" in text


def test_report_build_backlog_from_non_goals_and_blocked_tickets(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)
    t1 = _new_ticket(root, "Blocked ticket")
    text = t1.read_text(encoding="utf-8")
    text = text.replace("status: todo", "status: blocked")
    t1.write_text(text, encoding="utf-8")

    result = build_completion_report(root, SAMPLE)
    text = result.path.read_text(encoding="utf-8")
    assert "Backlog" in text
    assert "fancy dashboards" in text
    assert "Blocked ticket" in text


def test_report_build_non_destructive_without_force(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)

    first = build_completion_report(root, SAMPLE)
    assert first.written is True
    before = first.path.read_bytes()

    second = build_completion_report(root, SAMPLE)
    assert second.written is False
    assert second.diff_path is not None
    assert second.diff_path.exists()
    assert first.path.read_bytes() == before


def test_report_build_force_overwrites(tmp_path):
    root = _init_git_project(str(tmp_path))
    _write_requirements(root)

    first = build_completion_report(root, SAMPLE)
    t1 = _new_ticket(root, "New ticket after first build")
    _fill_completion_report(t1, outcome="added later", files="z.py", errors="none", verify="pytest — 1 passed")

    second = build_completion_report(root, SAMPLE, force=True)
    assert second.written is True
    assert "added later" in second.path.read_text(encoding="utf-8")


# --- CLI wiring ---------------------------------------------------------

def test_cli_report_build_creates_completion_doc():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        root = _init_git_project(td)
        _write_requirements(root)
        result = runner.invoke(main, ["dev", "report", "build", SAMPLE])
        assert result.exit_code == 0, result.output
        assert "Created" in result.output


def test_cli_report_build_non_destructive_message():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        root = _init_git_project(td)
        _write_requirements(root)
        runner.invoke(main, ["dev", "report", "build", SAMPLE])
        result = runner.invoke(main, ["dev", "report", "build", SAMPLE])
        assert result.exit_code == 0, result.output
        assert ".new" in result.output


def test_cli_report_build_force_flag():
    runner = CliRunner()
    with runner.isolated_filesystem() as td:
        root = _init_git_project(td)
        _write_requirements(root)
        runner.invoke(main, ["dev", "report", "build", SAMPLE])
        result = runner.invoke(main, ["dev", "report", "build", SAMPLE, "--force"])
        assert result.exit_code == 0, result.output
        assert "Created" in result.output
