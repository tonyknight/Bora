"""Install and uninstall the bora skill for AI coding tools.

Both Claude Code and OpenCode (and several other tools) discover skills as
directories containing a `SKILL.md` file. The format is identical across
tools; only the install location differs. This module owns the template
and the per-tool path registry.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .skill_pack import PACK_SKILLS, PACK_SKILL_NAMES_RE, SKILL_TEMPLATES, render_pack_skill

# A marker we look for in an existing SKILL.md before agreeing to remove it.
# Conservative: we only manage skills we wrote ourselves.
_OWNED_NAME_RE = re.compile(
    rf"^name:\s*({PACK_SKILL_NAMES_RE})\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class Tool:
    """A target tool that supports SKILL.md-style skills."""

    key: str           # CLI identifier, lowercase
    display: str       # Human-readable name for messages
    global_dir: Path   # Where ~/-level skills live for this tool
    project_dir: Path  # Where repo-local skills live for this tool


def _opencode_global_root() -> Path:
    """Resolve OpenCode's global config dir, honoring $XDG_CONFIG_HOME."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "opencode"


TOOLS: dict[str, Tool] = {
    "claude": Tool(
        key="claude",
        display="Claude Code",
        global_dir=Path.home() / ".claude" / "skills",
        project_dir=Path(".claude") / "skills",
    ),
    "opencode": Tool(
        key="opencode",
        display="OpenCode",
        global_dir=_opencode_global_root() / "skills",
        project_dir=Path(".opencode") / "skills",
    ),
    "cursor": Tool(
        key="cursor",
        display="Cursor",
        global_dir=Path.home() / ".cursor" / "skills",
        project_dir=Path(".cursor") / "skills",
    ),
}

SKILL_NAME = "bora"


def pack_root(tool: Tool, *, project_root: Optional[Path] = None) -> Path:
    """Directory that holds the skill pack (`bora/`, `bora-plan/`, …)."""
    if project_root is not None:
        return (project_root / tool.project_dir).resolve()
    return tool.global_dir


def skill_path(tool: Tool, *, project_root: Optional[Path] = None) -> Path:
    """Return the full path to a tool's bootstrap `bora` skill directory."""
    return pack_root(tool, project_root=project_root) / "bora"


def is_bora_skill(skill_md: Path) -> bool:
    """True if a SKILL.md file declares a bora-owned name in its frontmatter."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_OWNED_NAME_RE.search(text))


@dataclass
class InstallResult:
    tool: Tool
    path: Path
    overwritten: bool


def install(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> InstallResult:
    """Install the bora skill pack for `tool`. Raises FileExistsError if a
    non-bora SKILL.md is already at a pack path and `force` is False."""
    root = pack_root(tool, project_root=project_root)
    bora_md = root / "bora" / "SKILL.md"
    overwritten = bora_md.exists()
    for name in PACK_SKILLS:
        skill_md = root / name / "SKILL.md"
        if skill_md.exists() and not force and not is_bora_skill(skill_md):
            raise FileExistsError(
                f"A different SKILL.md already exists at {skill_md}. "
                f"Use --force to overwrite."
            )

    for name in PACK_SKILLS:
        target_dir = root / name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "SKILL.md").write_text(render_pack_skill(name), encoding="utf-8")
    return InstallResult(tool=tool, path=bora_md, overwritten=overwritten)


@dataclass
class UninstallResult:
    tool: Tool
    path: Path
    removed: bool
    reason: str = ""  # populated when removed=False


def uninstall(tool: Tool, *, project_root: Optional[Path] = None, force: bool = False) -> UninstallResult:
    """Remove the bora skill pack for `tool` if we own it."""
    root = pack_root(tool, project_root=project_root)
    bora_dir = root / "bora"
    bora_md = bora_dir / "SKILL.md"

    any_present = any((root / name).exists() for name in PACK_SKILLS)
    if not any_present:
        return UninstallResult(tool=tool, path=bora_dir, removed=False, reason="not installed")

    for name in PACK_SKILLS:
        skill_md = root / name / "SKILL.md"
        if skill_md.exists() and not is_bora_skill(skill_md) and not force:
            return UninstallResult(
                tool=tool,
                path=root / name,
                removed=False,
                reason="SKILL.md at this path is not bora's (use --force to remove anyway)",
            )

    for name in PACK_SKILLS:
        target = root / name
        if target.exists():
            shutil.rmtree(target)
    return UninstallResult(tool=tool, path=bora_dir, removed=True)


@dataclass
class Status:
    tool: Tool
    scope: str         # "global" or "project"
    path: Path
    installed: bool
    is_ours: bool      # True if installed AND looks like our SKILL.md


def list_status(*, project_root: Optional[Path] = None) -> list[Status]:
    """Return install status for every known tool, both global and project scopes
    (project only included if `project_root` is provided)."""
    out: list[Status] = []
    for tool in TOOLS.values():
        gpath = skill_path(tool)
        gskill = gpath / "SKILL.md"
        out.append(Status(
            tool=tool,
            scope="global",
            path=gpath,
            installed=gskill.exists(),
            is_ours=is_bora_skill(gskill),
        ))
        if project_root is not None:
            ppath = skill_path(tool, project_root=project_root)
            pskill = ppath / "SKILL.md"
            out.append(Status(
                tool=tool,
                scope="project",
                path=ppath,
                installed=pskill.exists(),
                is_ours=is_bora_skill(pskill),
            ))
    return out
