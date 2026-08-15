"""Refresh AGENTS.md and the skill pack to match this CLI version."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import __version__
from .paths import AGENTS_FILE, PROFILE_FILE
from .profile import read_profile
from .skill import PACK_SKILLS, TOOLS, install as install_skill, skill_path
from .templates import (
    AGENTS_TEMPLATE_VERSION,
    MANAGED_END,
    MANAGED_START_RE,
    render_agents_md,
    replace_managed_region,
)

START_RE = MANAGED_START_RE


@dataclass
class UpgradePlan:
    """What `bora dev upgrade` would do (or did)."""

    agents_action: str  # "write" | "replace-managed" | "skip" | "stale-unmarked"
    agents_version: Optional[str]
    skill_paths: list[Path] = field(default_factory=list)
    profile_version: Optional[str] = None
    dirty_unmarked: bool = False


def agents_managed_version(text: str) -> Optional[str]:
    match = START_RE.search(text)
    if match:
        return match.group(1)
    return None


def agents_template_is_stale(root: Path) -> bool:
    path = root / AGENTS_FILE
    if not path.exists():
        return True
    version = agents_managed_version(path.read_text(encoding="utf-8"))
    if version is None:
        return True
    return version != AGENTS_TEMPLATE_VERSION


def agents_has_uncommitted_changes(root: Path) -> bool:
    git_dir = root / ".git"
    if not git_dir.exists():
        return False
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", AGENTS_FILE],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _installed_skill_targets(root: Path) -> list[tuple[object, Optional[Path]]]:
    """Return (tool, project_root_or_None) for every already-installed pack."""
    out: list[tuple[object, Optional[Path]]] = []
    for tool in TOOLS.values():
        gpath = skill_path(tool) / "SKILL.md"
        if gpath.exists():
            out.append((tool, None))
        ppath = skill_path(tool, project_root=root) / "SKILL.md"
        if ppath.exists():
            out.append((tool, root))
    return out


def inspect_upgrade(root: Path) -> UpgradePlan:
    agents = root / AGENTS_FILE
    profile = read_profile(root)
    plan = UpgradePlan(
        agents_action="skip",
        agents_version=None,
        profile_version=(profile or {}).get("version"),
    )
    if not agents.exists():
        plan.agents_action = "write"
    else:
        text = agents.read_text(encoding="utf-8")
        plan.agents_version = agents_managed_version(text)
        if plan.agents_version is None:
            plan.agents_action = "stale-unmarked"
            plan.dirty_unmarked = agents_has_uncommitted_changes(root)
        elif plan.agents_version != AGENTS_TEMPLATE_VERSION:
            plan.agents_action = "replace-managed"
        else:
            plan.agents_action = "replace-managed"  # still rewrite managed body (idempotent)
    for tool, project_root in _installed_skill_targets(root):
        base = skill_path(tool, project_root=project_root).parent
        for name in PACK_SKILLS:
            plan.skill_paths.append(base / name / "SKILL.md")
    return plan


def apply_upgrade(
    root: Path,
    *,
    dry_run: bool = False,
    agents_only: bool = False,
    skills_only: bool = False,
    force: bool = False,
) -> UpgradePlan:
    plan = inspect_upgrade(root)
    if dry_run:
        return plan

    if not skills_only:
        agents = root / AGENTS_FILE
        if plan.agents_action == "stale-unmarked" and plan.dirty_unmarked and not force:
            raise PermissionError(
                "AGENTS.md has uncommitted changes. Commit or stash it, then re-run; "
                "or pass --force."
            )
        if plan.agents_action == "stale-unmarked" or not agents.exists():
            agents.write_text(render_agents_md(), encoding="utf-8")
        elif plan.agents_action == "replace-managed":
            text = agents.read_text(encoding="utf-8")
            agents.write_text(replace_managed_region(text), encoding="utf-8")

    if not agents_only:
        seen: set[tuple[str, str]] = set()
        for tool, project_root in _installed_skill_targets(root):
            key = (tool.key, str(project_root) if project_root else "global")
            if key in seen:
                continue
            seen.add(key)
            install_skill(tool, project_root=project_root, force=True)

    # Bump profile version without resetting initialized_at.
    profile_path = root / PROFILE_FILE
    if profile_path.exists():
        data = read_profile(root) or {}
        data["version"] = __version__
        profile_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return inspect_upgrade(root)
