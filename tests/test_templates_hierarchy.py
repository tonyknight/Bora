from bora.templates import REQUIREMENTS_MD_TEMPLATE, render_project_md


def test_render_project_md_with_tags():
    text = render_project_md(
        hierarchy=["QromaCore", "Hamburg", "Gallery Refactor"],
        tags=["Codebase", "Release Train", "Project"],
        today="2026-08-14",
    )
    assert "codebase: QromaCore" in text
    assert "release_train: Hamburg" in text
    assert "project: Gallery Refactor" in text
    assert "hierarchy:" in text
    assert "last_reviewed: 2026-08-14" in text
    assert 'focus: ""' in text
    assert "## Background" in text


def test_render_project_md_without_tags_has_hierarchy_only():
    text = render_project_md(
        hierarchy=["Acme", "Auth"],
        tags=None,
        today="2026-08-14",
    )
    assert "hierarchy:" in text
    assert "codebase:" not in text
    assert "tags:" not in text


def test_requirements_template_has_required_headings():
    text = REQUIREMENTS_MD_TEMPLATE.format(today="2026-08-14", project_name="Gallery Refactor")
    for heading in [
        "## Overview",
        "## Goals",
        "## Non-goals",
        "## Architecture",
        "## Requirements",
        "## Acceptance criteria",
        "## Testing requirements",
        "## Commit criteria",
        "## Tasks Breakdown",
        "## Risks and assumptions",
        "## Open questions",
        "### Components",
        "### Data model",
        "### Key flows",
    ]:
        assert heading in text
    assert "{task name}" in text or "task name" in text.lower()
