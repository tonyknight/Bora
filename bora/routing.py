"""Provider-neutral model-tier vocabulary and `.bora/models.yaml` resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<frontmatter>.*?)\n---\s*\n(?P<body>.*)\Z",
    re.DOTALL,
)


def _parse_frontmatter_text(text: str) -> dict:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = yaml.safe_load(match.group("frontmatter")) or {}
    return data if isinstance(data, dict) else {}


ROUTING_YAML_VERSION = 1
ROUTING_FILE = "routing.yaml"


@dataclass
class ProjectRouting:
    """The project-level `routing.yaml` resolution layer (Requirements §7).

    Generated by `bora dev routing sync`, then user-editable. Distinct from
    the repo-wide preference catalog in `.bora/models.yaml`.
    """

    version: int
    host: Optional[str]
    synced: Optional[str]
    source: Optional[str]
    tiers: dict[str, Optional[str]]
    pinned: list[str] = field(default_factory=list)
    available: list[str] = field(default_factory=list)
    unmatched_aliases: dict[str, list[str]] = field(default_factory=dict)


def _routing_yaml_path(root: Path, project_path: str) -> Path:
    from .paths import project_dir

    return project_dir(root, project_path) / ROUTING_FILE


def _validate_routing_file(data: Any, path: Path) -> None:
    if not isinstance(data, dict):
        raise RoutingConfigError(f"{path.name} must contain a mapping at the top level")
    version = data.get("version")
    if version != ROUTING_YAML_VERSION:
        raise RoutingConfigError(
            f"{path.name} has unsupported version {version!r}; expected {ROUTING_YAML_VERSION}"
        )
    tiers = data.get("tiers") or {}
    if not isinstance(tiers, dict):
        raise RoutingConfigError(f"'tiers' in {path.name} must be a mapping")
    for name, value in tiers.items():
        if name not in VALID_TIERS:
            raise RoutingConfigError(
                f"Unknown tier name '{name}' in {path.name}. "
                f"Valid tiers: {', '.join(sorted(VALID_TIERS))}"
            )
        if value is not None and not isinstance(value, str):
            raise RoutingConfigError(f"Tier '{name}' in {path.name} must be a string or null")
    available = data.get("available") or []
    if not isinstance(available, list) or not all(isinstance(a, str) for a in available):
        raise RoutingConfigError(f"'available' in {path.name} must be a list of strings")


def load_routing_file(root: Path, project_path: str) -> Optional[ProjectRouting]:
    """Load and validate a project's `routing.yaml`.

    Missing file is not an error: returns ``None``. Invalid YAML or an
    invalid structure raises ``RoutingConfigError`` naming the file.
    """
    path = _routing_yaml_path(root, project_path)
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RoutingConfigError(f"Invalid YAML in {path.name}: {exc}") from exc
    _validate_routing_file(data, path)

    tiers = {name: data.get("tiers", {}).get(name) for name in VALID_TIERS}
    pinned = [t for t in (data.get("pinned") or []) if t in VALID_TIERS]
    return ProjectRouting(
        version=data["version"],
        host=data.get("host"),
        synced=data.get("synced"),
        source=data.get("source"),
        tiers=tiers,
        pinned=pinned,
        available=list(data.get("available") or []),
        unmatched_aliases=dict(data.get("unmatched_aliases") or {}),
    )


def write_routing_file(
    root: Path,
    project_path: str,
    routing: "ProjectRouting",
    *,
    repin: bool = False,
    dry_run: bool = False,
) -> ProjectRouting:
    """Write `routing.yaml`, preserving hand-edited (pinned) tier values.

    A tier is pinned when the file already on disk holds a different value
    for that tier than what this write would otherwise set — i.e. a human
    edited it since the last write. Pinned tiers are kept as-is and added to
    ``pinned`` unless ``repin`` discards every existing pin and writes the
    incoming values verbatim.

    ``dry_run`` computes and returns the merged result — including which
    tiers would be pinned or preserved by this write — without touching
    disk. Callers that need to report on a pending write (warnings, summary
    counts) should always call this rather than inspecting the file as it
    stood *before* the call, since pin status is only known once merged.
    """
    path = _routing_yaml_path(root, project_path)
    existing = None if repin else load_routing_file(root, project_path)

    final_tiers: dict[str, Optional[str]] = {}
    final_pinned: list[str] = [] if repin else list(routing.pinned)
    for tier in VALID_TIERS:
        incoming = routing.tiers.get(tier)
        if not repin and existing is not None:
            prior = existing.tiers.get(tier)
            was_pinned = tier in existing.pinned
            if was_pinned or (prior is not None and prior != incoming):
                final_tiers[tier] = prior
                if tier not in final_pinned:
                    final_pinned.append(tier)
                continue
        final_tiers[tier] = incoming

    result = ProjectRouting(
        version=ROUTING_YAML_VERSION,
        host=routing.host,
        synced=routing.synced,
        source=routing.source,
        tiers=final_tiers,
        pinned=final_pinned,
        available=list(routing.available),
        unmatched_aliases=dict(routing.unmatched_aliases),
    )

    if dry_run:
        return result

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": result.version,
        "host": result.host,
        "synced": result.synced,
        "source": result.source,
        "tiers": dict(result.tiers),
        "pinned": list(result.pinned),
        "available": list(result.available),
        "unmatched_aliases": dict(result.unmatched_aliases),
    }
    header = (
        "# Generated by bora dev routing sync. Edit tier mappings freely;\n"
        "# edited entries are pinned and survive re-sync.\n"
    )
    path.write_text(header + yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return result


def briefing_frontmatter(root: Path, project_path: str) -> dict:
    """Return the project briefing YAML frontmatter, or {} if missing/unreadable."""
    from .paths import project_file

    path = project_file(root, project_path)
    if not path.is_file():
        return {}
    try:
        return _parse_frontmatter_text(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}


def project_is_routing_opted_in(root: Path, project_path: str) -> bool:
    """True only when the briefing has ``routing: true``."""
    return briefing_frontmatter(root, project_path).get("routing") is True


def routing_cache_for_host(frontmatter: dict, host: str) -> dict[str, str]:
    """Return last-resolved slugs for ``host``. Malformed cache → empty dict."""
    cache = frontmatter.get("routing_cache")
    if not isinstance(cache, dict):
        return {}
    host_map = cache.get(host)
    if not isinstance(host_map, dict):
        return {}
    out: dict[str, str] = {}
    for tier, slug in host_map.items():
        if tier in VALID_TIERS and isinstance(slug, str) and slug.strip():
            out[str(tier)] = slug.strip()
    return out


MATCH_MATCHED = "matched"
MATCH_ASK = "ask"


@dataclass
class TierMatch:
    """Result of matching one tier's alias list against available host models."""

    status: str
    slug: Optional[str] = None
    candidates: list[str] = field(default_factory=list)
    suggest: Optional[str] = None
    alias: Optional[str] = None
    stale_routing_slug: Optional[str] = None


def _normalize_model_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\-_/\s]", " ", text.lower())
    return " ".join(cleaned.split())


def _model_tokens(text: str) -> list[str]:
    return [part for part in re.split(r"[\s\-_]+", _normalize_model_text(text)) if part]


def _score_alias(alias: str, available: str) -> int:
    needle = _normalize_model_text(alias)
    haystack = _normalize_model_text(available)
    if not needle or not haystack:
        return 0
    if needle == haystack:
        return 3
    if needle in haystack or haystack in needle:
        return 2
    haystack_tokens = set(_model_tokens(available))
    if any(token in haystack or token in haystack_tokens for token in _model_tokens(alias)):
        return 1
    return 0


def match_tier(
    aliases: list[str],
    available: list[str],
    cache_slug: Optional[str] = None,
) -> TierMatch:
    """Fuzzy-match ordered aliases to injected available model names.

    Unique hit → matched. Two or more hits for an alias, or none at all → ask.
    ``cache_slug`` is suggested on ask only when it is still in ``available``.
    """
    models = [item.strip() for item in available if isinstance(item, str) and item.strip()]
    cache_ok = cache_slug if isinstance(cache_slug, str) and cache_slug in models else None
    for alias in aliases:
        scored: dict[str, int] = {}
        for model in models:
            score = _score_alias(alias, model)
            if score > 0:
                scored[model] = score
        if not scored:
            continue
        best = max(scored.values())
        winners: list[str] = []
        seen: set[str] = set()
        for model, score in scored.items():
            if score != best:
                continue
            key = _normalize_model_text(model)
            if key in seen:
                continue
            seen.add(key)
            winners.append(model)
        if len(winners) == 1:
            return TierMatch(status=MATCH_MATCHED, slug=winners[0], alias=alias)
        return TierMatch(
            status=MATCH_ASK,
            candidates=winners,
            suggest=cache_ok,
            alias=alias,
        )
    return TierMatch(status=MATCH_ASK, candidates=[], suggest=cache_ok)


def resolve_session(
    tiers: dict[str, list[str]],
    available: list[str],
    host: str,
    cache: Optional[dict] = None,
    routing_yaml: Optional["ProjectRouting"] = None,
) -> dict[str, TierMatch]:
    """Match each tier for ``host``. Cache for other hosts is ignored.

    Precedence (0.8.0, Requirements §11): a `routing.yaml` slug still present
    in ``available`` wins outright, skipping catalog matching for that tier —
    this covers both pinned and unpinned entries identically, since either
    way it is the last known-good resolution for this host and re-deriving
    it via fuzzy match every session is exactly what persisting it avoids.
    A `routing.yaml` slug **absent** from ``available`` is stale: fall
    through to catalog matching (then briefing ``cache``, then ask) and
    record the stale slug on the result so a caller can suggest a re-sync.
    """
    cache = cache or {}
    raw_host = cache.get(host) if isinstance(cache, dict) else None
    host_cache = raw_host if isinstance(raw_host, dict) else {}
    resolved: dict[str, TierMatch] = {}
    for tier, aliases in tiers.items():
        routing_slug = routing_yaml.tiers.get(tier) if routing_yaml else None
        if routing_slug and routing_slug in available:
            resolved[tier] = TierMatch(status=MATCH_MATCHED, slug=routing_slug)
            continue
        hint = host_cache.get(tier)
        cache_slug = hint if isinstance(hint, str) else None
        match = match_tier(list(aliases), available, cache_slug=cache_slug)
        if routing_slug:
            match.stale_routing_slug = routing_slug
        resolved[tier] = match
    return resolved
