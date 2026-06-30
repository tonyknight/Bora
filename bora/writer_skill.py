"""Obsidian skill installer/uninstaller: bora write skill install/uninstall obsidian."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from .templates import OBSIDIAN_MANIFEST_JSON, OBSIDIAN_README_MD, OBSIDIAN_SKILL_MD

_PLUGIN_DIR = ".obsidian/plugins/bora-writer"
_MARKER = "bora-writer"


@dataclass
class InstallResult:
    path: Path
    overwritten: bool


@dataclass
class UninstallResult:
    path: Path
    removed: bool
    reason: str = ""


def install_obsidian(project_root: Path, force: bool = False) -> InstallResult:
    """Create .obsidian/plugins/bora-writer/ with SKILL.md, manifest.json, README.md."""
    plugin_dir = project_root / _PLUGIN_DIR
    already_exists = plugin_dir.exists()

    if already_exists and not force:
        raise FileExistsError(
            f"{_PLUGIN_DIR} already exists. Use --force to overwrite."
        )

    plugin_dir.mkdir(parents=True, exist_ok=True)

    (plugin_dir / "SKILL.md").write_text(OBSIDIAN_SKILL_MD, encoding="utf-8")
    (plugin_dir / "manifest.json").write_text(OBSIDIAN_MANIFEST_JSON, encoding="utf-8")
    (plugin_dir / "README.md").write_text(OBSIDIAN_README_MD, encoding="utf-8")

    return InstallResult(path=plugin_dir, overwritten=already_exists)


def uninstall_obsidian(project_root: Path, force: bool = False) -> UninstallResult:
    """Remove .obsidian/plugins/bora-writer/."""
    plugin_dir = project_root / _PLUGIN_DIR

    if not plugin_dir.exists():
        return UninstallResult(path=plugin_dir, removed=False, reason="not installed")

    # Safety check: only remove if it looks like ours (has SKILL.md)
    if not force and not (plugin_dir / "SKILL.md").exists():
        return UninstallResult(
            path=plugin_dir,
            removed=False,
            reason="SKILL.md not found — use --force to remove anyway",
        )

    shutil.rmtree(plugin_dir)
    return UninstallResult(path=plugin_dir, removed=True)
