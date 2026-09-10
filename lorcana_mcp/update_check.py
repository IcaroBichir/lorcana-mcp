"""Best-effort "a newer lorcana-mcp is on PyPI" check.

MCP has no mechanism for a server to tell a client it is out of date, so
this does the next best thing: about once a day, ask PyPI for the latest
published version. If it is newer than the running one, callers surface a
short notice — currently on the `serve` startup line (stderr, which Claude
Code shows in its MCP logs and Claude Desktop writes to its log files) and
appended to `get_meta`'s output (so it reaches the model's context and
gets relayed).

Guarantees:
  * Never raises. Every failure path (offline, timeout, PyPI down, junk
    payload, unwritable cache dir) resolves to "no notice", silently.
  * Never blocks the server. The answer is read from a local cache only;
    refreshing that cache from the network happens on a fire-and-forget
    daemon thread, so a fresh install just sees the notice one session
    late instead of stalling startup.
  * One network call per 24h, cached on disk beside the card-data cache.
  * Full opt-out: set LORCANA_MCP_NO_UPDATE_CHECK to any non-empty value.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

_PYPI_JSON = "https://pypi.org/pypi/lorcana-mcp/json"
_CACHE_FILE = Path.home() / ".cache" / "lorcana-mcp" / "update_check.json"
_TTL = 86_400  # 24h — same cadence as the card-data cache
_TIMEOUT = 3.0  # seconds; the fetch runs off-thread but stays bounded anyway
OPT_OUT_ENV = "LORCANA_MCP_NO_UPDATE_CHECK"

_refresh_lock = threading.Lock()
_refresh_started = False


def _opted_out() -> bool:
    return bool(os.environ.get(OPT_OUT_ENV, "").strip())


def installed_version() -> str | None:
    try:
        return _pkg_version("lorcana-mcp")
    except PackageNotFoundError:
        return None


def _version_tuple(v: str) -> tuple[int, ...] | None:
    """(1, 2, 3) from "1.2.3". Returns None for anything with a
    pre-release / dev / local / non-numeric segment, so a stable install is
    never nagged about an "update" to an rc, and a weird string never trips
    a false alarm."""
    out: list[int] = []
    for part in v.strip().split("."):
        if not part.isdigit():
            return None
        out.append(int(part))
    return tuple(out) or None


def _is_newer(candidate: str, current: str) -> bool:
    c, cur = _version_tuple(candidate), _version_tuple(current)
    if c is None or cur is None:
        return False
    return c > cur


def _cache_fresh() -> dict | None:
    try:
        data = json.loads(_CACHE_FILE.read_text())
        if isinstance(data, dict) and (time.time() - float(data["ts"])) <= _TTL:
            return data
    except Exception:
        pass
    return None


def _write_cache(latest: str | None) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps({"ts": time.time(), "latest": latest}))
    except Exception:
        pass


def _fetch_latest_from_pypi() -> str | None:
    try:
        req = urllib.request.Request(
            _PYPI_JSON, headers={"User-Agent": "lorcana-mcp-update-check"}
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read())
        latest = payload["info"]["version"]
        return latest if isinstance(latest, str) and latest else None
    except Exception:
        return None


def _maybe_refresh_async() -> None:
    """Kick off a one-shot background cache refresh, at most once per process."""
    global _refresh_started
    if _opted_out():
        return
    with _refresh_lock:
        if _refresh_started:
            return
        _refresh_started = True

    def _run() -> None:
        _write_cache(_fetch_latest_from_pypi())

    threading.Thread(
        target=_run, name="lorcana-mcp-update-check", daemon=True
    ).start()


def available_update() -> str | None:
    """The newer version string if PyPI has one published, else None.

    Reads only the local cache; on a cache miss/stale it warms the cache in
    the background and returns None for this call.
    """
    if _opted_out():
        return None
    current = installed_version()
    if not current:
        return None
    cached = _cache_fresh()
    if cached is None:
        _maybe_refresh_async()
        return None
    latest = cached.get("latest")
    if isinstance(latest, str) and _is_newer(latest, current):
        return latest
    return None


def startup_stderr_notice() -> None:
    """Print a one-line update notice to stderr if outdated. Safe to call
    unconditionally right before `mcp.run()`."""
    try:
        newer = available_update()
        if newer:
            print(
                f"[lorcana-mcp] a newer version is available: "
                f"{installed_version()} -> {newer}. "
                f"Update with `pip install -U lorcana-mcp` (or re-download the "
                f".mcpb bundle). Set {OPT_OUT_ENV}=1 to silence this check.",
                file=sys.stderr,
                flush=True,
            )
    except Exception:
        pass


def get_meta_notice() -> str:
    """Trailing markdown block for get_meta's output when outdated, else ""."""
    try:
        newer = available_update()
        if not newer:
            return ""
        return (
            "\n\n---\n"
            f"_A newer **lorcana-mcp** is on PyPI: {installed_version()} → {newer}. "
            "The metagame snapshot above ships with the package, so a newer release "
            "may carry a fresher `META_SNAPSHOT_DATE` and tournament data. "
            "`pip install -U lorcana-mcp` (or re-download the .mcpb); "
            f"set `{OPT_OUT_ENV}=1` to silence._"
        )
    except Exception:
        return ""
