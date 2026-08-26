"""Endpoint model discovery. The only module in Bora permitted network I/O.

Enabled solely by `bora dev routing sync --probe <url>`. Every other command
and code path stays offline (Requirements v0.8.0 §10).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Optional

Transport = Callable[[str, dict[str, str], float], tuple[int, bytes]]


class ProbeError(RuntimeError):
    """The endpoint could not be reached, or returned no recognizable model list."""


def _default_transport_get(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ProbeError(f"Could not reach {url}: {exc}") from exc


def _parse_openai(body: bytes) -> Optional[list[str]]:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("data")
    if not isinstance(items, list):
        return None
    ids = [item.get("id") for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)]
    return ids if len(ids) == len(items) else None


def _parse_ollama(body: bytes) -> Optional[list[str]]:
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("models")
    if not isinstance(items, list):
        return None
    names = [item.get("name") for item in items if isinstance(item, dict) and isinstance(item.get("name"), str)]
    return names if len(names) == len(items) else None


def strip_userinfo(url: str) -> str:
    """Remove any `user:pass@` credential from a URL before it is persisted."""
    parts = urllib.parse.urlsplit(url)
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    return urllib.parse.urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def probe_models(
    base_url: str,
    *,
    token: Optional[str] = None,
    timeout: float = 10.0,
    transport: Optional[Transport] = None,
) -> list[str]:
    """Enumerate models from an OpenAI-compatible or Ollama endpoint.

    Tries `GET {base_url}/v1/models` then `GET {base_url}/api/tags`, in that
    order. A connection-level failure (unreachable host, timeout) aborts
    immediately without trying the second shape — retrying against the same
    dead host is pointless. An HTTP-level response that doesn't match either
    shape (404, wrong body) falls through to the next shape; if neither
    matches, raises ``ProbeError`` naming ``base_url``.
    """
    fetch = transport or _default_transport_get
    base = base_url.rstrip("/")
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    attempts: list[tuple[str, Callable[[bytes], Optional[list[str]]]]] = [
        (f"{base}/v1/models", _parse_openai),
        (f"{base}/api/tags", _parse_ollama),
    ]
    last_status: Optional[int] = None
    for url, parse in attempts:
        status, body = fetch(url, headers, timeout)
        last_status = status
        if 200 <= status < 300:
            models = parse(body)
            if models is not None:
                return models

    raise ProbeError(
        f"{base_url} did not return a recognizable model list (last status {last_status})"
    )
