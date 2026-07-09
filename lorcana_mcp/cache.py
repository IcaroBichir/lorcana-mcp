"""File-based cache for Lorcana API responses (~/.cache/lorcana-mcp/card_data.json)."""
from __future__ import annotations

import json
import time
from pathlib import Path

_CACHE_DIR = Path.home() / ".cache" / "lorcana-mcp"
_CACHE_FILE = _CACHE_DIR / "card_data.json"
_TTL = 86_400  # 24 hours — card data is stable within a day


def _load() -> dict:
    if not _CACHE_FILE.exists():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(json.dumps(data))


def get(key: str) -> dict | list | None:
    entry = _load().get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > _TTL:
        return None
    return entry["cards"]


def set(key: str, cards: dict | list) -> None:
    data = _load()
    data[key] = {"ts": time.time(), "cards": cards}
    _save(data)


def clear() -> int:
    data = _load()
    count = len(data)
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()
    return count


def stats() -> dict:
    data = _load()
    now = time.time()
    return {
        "entries": len(data),
        "expired": sum(1 for v in data.values() if now - v["ts"] > _TTL),
        "size_bytes": _CACHE_FILE.stat().st_size if _CACHE_FILE.exists() else 0,
    }
