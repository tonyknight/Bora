"""Provider-neutral model-tier vocabulary and `.bora/models.yaml` resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

VALID_TIERS = frozenset({"premium", "standard", "economy", "local"})

DEFAULT_SKILL_TIERS = {
    "bora": "standard",
    "bora-design": "premium",
    "bora-plan": "premium",
    "bora-tdd": "premium",
    "bora-execute": "standard",
    "bora-worktree": "economy",
    "bora-verify": "economy",
    "bora-review": "premium",
    "bora-debug": "premium",
    "bora-finish": "economy",
}

MODELS_YAML = ".bora/models.yaml"


class RoutingConfigError(ValueError):
    """Invalid `.bora/models.yaml` routing configuration."""


@dataclass
class EffectiveRouting:
    enabled: bool
    tiers: dict[str, list[str]]
    skill_tiers: dict[str, str]


def load_models_config(root: Path) -> Optional[dict]:
    """Load and validate `.bora/models.yaml`.

    Missing file is not an error: returns ``None``. Invalid YAML or an
    invalid routing structure raises ``RoutingConfigError``.
    """
    path = root / MODELS_YAML
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RoutingConfigError(f"Invalid YAML in {MODELS_YAML}: {exc}") from exc
    _validate_config(data)
    return data


def resolve_effective_routing(root: Path) -> EffectiveRouting:
    """Return effective routing for ``root`` without writing files or I/O beyond yaml."""
    data = load_models_config(root)
    skill_tiers = dict(DEFAULT_SKILL_TIERS)
    if data is None:
        return EffectiveRouting(enabled=False, tiers={}, skill_tiers=skill_tiers)

    routing = data["routing"]
    enabled = bool(routing.get("enabled", False))
    raw_tiers = routing.get("tiers") or {}
    tiers = {name: list(aliases) for name, aliases in raw_tiers.items()}
    overrides = routing.get("skills") or {}
    skill_tiers.update(overrides)
    return EffectiveRouting(enabled=enabled, tiers=tiers, skill_tiers=skill_tiers)


def _aliases_from_value(name: str, value: Any) -> list[str]:
    """Normalize a tier value to an ordered non-empty list of aliases."""
    if isinstance(value, str):
        aliases = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        aliases = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise RoutingConfigError(
                    f"Tier '{name}' identifier must be a non-empty string"
                )
            aliases.append(item.strip())
    else:
        raise RoutingConfigError(
            f"Tier '{name}' identifier must be a non-empty string or list of strings"
        )
    if not aliases:
        raise RoutingConfigError(
            f"Tier '{name}' must have at least one non-empty alias"
        )
    return aliases


def _validate_config(data: Any) -> None:
    if not isinstance(data, dict):
        raise RoutingConfigError(
            f"{MODELS_YAML} must contain a mapping at the top level"
        )
    routing = data.get("routing")
    if not isinstance(routing, dict):
        raise RoutingConfigError(f"{MODELS_YAML} must contain a 'routing' mapping")

    tiers = routing.get("tiers")
    if tiers is not None:
        if not isinstance(tiers, dict):
            raise RoutingConfigError("'routing.tiers' must be a mapping")
        for name, identifier in list(tiers.items()):
            if name not in VALID_TIERS:
                raise RoutingConfigError(
                    f"Unknown tier name '{name}'. "
                    f"Valid tiers: {', '.join(sorted(VALID_TIERS))}"
                )
            tiers[name] = _aliases_from_value(name, identifier)

    skills = routing.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            raise RoutingConfigError("'routing.skills' must be a mapping")
        for skill, tier in skills.items():
            if skill not in DEFAULT_SKILL_TIERS:
                raise RoutingConfigError(
                    f"Unknown skill '{skill}' in routing.skills"
                )
            if tier not in VALID_TIERS:
                raise RoutingConfigError(
                    f"Invalid tier '{tier}' for skill '{skill}'. "
                    f"Valid tiers: {', '.join(sorted(VALID_TIERS))}"
                )
