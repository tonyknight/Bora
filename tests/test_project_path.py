from datetime import date
from pathlib import Path

import pytest

from bora.paths import (
    ProjectPathError,
    dated_filename,
    discover_project_file,
    discover_requirements_file,
    parse_project_path,
    parse_tags,
    project_dir,
    project_file,
    project_name,
    project_tickets_dir,
    requirements_file,
    split_trailing_tags,
    status_file,
    tag_key,
)


def test_parse_depth_2_and_3():
    assert parse_project_path("Acme/Auth") == ("Acme", "Auth")
    assert parse_project_path("QromaCore/Hamburg/Gallery Refactor") == (
        "QromaCore",
        "Hamburg",
        "Gallery Refactor",
    )


def test_parse_depth_4():
    assert parse_project_path("Acme/Platform/Auth/OAuth Refresh") == (
        "Acme",
        "Platform",
        "Auth",
        "OAuth Refresh",
    )


@pytest.mark.parametrize(
    "raw",
    ["Foo", "", "a//b", "/abs/path", "a/../b", "a/.", "a/ /b", "a/", "/a/b"],
)
def test_parse_rejects(raw):
    with pytest.raises(ProjectPathError):
        parse_project_path(raw)


def test_parse_strips_surrounding_quotes():
    assert parse_project_path('"QromaCore/Hamburg/Gallery Refactor"') == (
        "QromaCore",
        "Hamburg",
        "Gallery Refactor",
    )
    assert parse_project_path("'Acme/Auth'") == ("Acme", "Auth")


def test_split_trailing_tags():
    path, tags = split_trailing_tags(
        "QromaCore/Hamburg/Gallery Refactor [Codebase,Release Train,Project]"
    )
    assert path == "QromaCore/Hamburg/Gallery Refactor"
    assert tags == "Codebase,Release Train,Project"


def test_split_trailing_tags_noop():
    path, tags = split_trailing_tags("QromaCore/Hamburg/Gallery Refactor")
    assert path == "QromaCore/Hamburg/Gallery Refactor"
    assert tags is None


def test_parse_tags_csv_and_brackets():
    assert parse_tags('Codebase,"Release Train",Project') == [
        "Codebase",
        "Release Train",
        "Project",
    ]
    assert parse_tags("[Codebase,Release Train,Project]") == [
        "Codebase",
        "Release Train",
        "Project",
    ]


def test_tag_key_slugifies():
    assert tag_key("Release Train") == "release_train"
    assert tag_key("Codebase") == "codebase"


def test_resolvers_join_under_docs_ai(tmp_path):
    p = "QromaCore/Hamburg/Gallery Refactor"
    assert project_dir(tmp_path, p) == tmp_path / "docs/ai/QromaCore/Hamburg/Gallery Refactor"
    assert project_name(parse_project_path(p)) == "Gallery Refactor"
    assert status_file(tmp_path, p) == tmp_path / "docs/ai/QromaCore/Hamburg/Gallery Refactor/Status.md"
    assert project_tickets_dir(tmp_path, p) == (
        tmp_path / "docs/ai/QromaCore/Hamburg/Gallery Refactor/tickets"
    )


def test_dated_filename():
    d = date(2026, 8, 14)
    assert dated_filename(d, "Gallery Refactor") == "(2026-08-14) Gallery Refactor.md"
    assert dated_filename(d, "Gallery Refactor", requirements=True) == (
        "(2026-08-14) Gallery Refactor Requirements.md"
    )


def test_discover_does_not_confuse_briefing_and_requirements(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    brief = d / "(2026-08-14) Gallery Refactor.md"
    req = d / "(2026-08-14) Gallery Refactor Requirements.md"
    brief.write_text("b")
    req.write_text("r")
    assert discover_project_file(d, "Gallery Refactor") == brief
    assert discover_requirements_file(d, "Gallery Refactor") == req


def test_discover_picks_latest_date(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    older = d / "(2026-01-01) Gallery Refactor.md"
    newer = d / "(2026-08-14) Gallery Refactor.md"
    older.write_text("old")
    newer.write_text("new")
    assert discover_project_file(d, "Gallery Refactor") == newer


def test_project_file_constructs_today_when_missing(tmp_path):
    p = "Acme/Auth"
    today = date(2026, 8, 14)
    got = project_file(tmp_path, p, today=today)
    assert got == tmp_path / "docs/ai/Acme/Auth/(2026-08-14) Auth.md"
    got_r = requirements_file(tmp_path, p, today=today)
    assert got_r == tmp_path / "docs/ai/Acme/Auth/(2026-08-14) Auth Requirements.md"
