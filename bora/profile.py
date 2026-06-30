"""Profile management for .bora/profile.json."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

PROFILE_FILE = ".bora/profile.json"
CURRENT_VERSION = "0.3.0"


def profile_path(root: Path) -> Path:
    return root / PROFILE_FILE


def read_profile(root: Path) -> Optional[dict]:
    """Return parsed profile.json, or None if it doesn't exist or is unreadable."""
    path = profile_path(root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_profile(root: Path, profile: str) -> None:
    """Write .bora/profile.json with the given profile value."""
    path = profile_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": CURRENT_VERSION,
        "profile": profile,
        "initialized_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "auto_archive": True,
            "research_log_mode": "full_interaction",
        },
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def require_profile(root: Path, expected: str, skip_check: bool = False) -> None:
    """Verify the active profile matches `expected`.

    If no profile.json exists, prompts the user to choose a profile and
    writes it before continuing. If the profile mismatches `expected`, prints
    a clear error and exits with code 1.
    """
    if skip_check:
        return

    path = profile_path(root)
    if not path.exists():
        chosen = click.prompt(
            "No profile found. Choose profile",
            type=click.Choice(["dev", "write"]),
        )
        write_profile(root, chosen)
        profile = chosen
    else:
        data = read_profile(root) or {}
        profile = data.get("profile", "")

    if profile != expected:
        click.echo(
            f"❌ Profile locked to '{profile}'. "
            f"Use 'bora {profile} <command>' or edit .bora/profile.json.",
            err=True,
        )
        sys.exit(1)
