"""Tests for update_check.py — no real network; the fetch is always stubbed."""
from __future__ import annotations

import json
import time

import pytest

from lorcana_mcp import update_check as uc


@pytest.fixture
def opted_in(monkeypatch, tmp_path):
    """Undo conftest's global opt-out, point the cache at a tmp file, and
    stub the network fetch so nothing leaves the process."""
    monkeypatch.delenv(uc.OPT_OUT_ENV, raising=False)
    monkeypatch.setattr(uc, "_CACHE_FILE", tmp_path / "update_check.json")
    monkeypatch.setattr(uc, "_refresh_started", False)
    calls: list[int] = []

    def _fake_fetch() -> str | None:
        calls.append(1)
        return _fake_fetch.result

    _fake_fetch.result = None
    monkeypatch.setattr(uc, "_fetch_latest_from_pypi", _fake_fetch)
    return _fake_fetch, calls


def _write_cache(uc_mod, latest, *, age=0.0):
    uc_mod._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    uc_mod._CACHE_FILE.write_text(json.dumps({"ts": time.time() - age, "latest": latest}))


# ── version comparison ───────────────────────────────────────────────────────

@pytest.mark.parametrize("cand,cur,expected", [
    ("2.3.0", "2.2.0", True),
    ("2.2.1", "2.2.0", True),
    ("2.10.0", "2.9.0", True),
    ("2.2.0", "2.2.0", False),
    ("2.1.0", "2.2.0", False),
    ("2.2", "2.2.0", False),          # (2,2) < (2,2,0) is False, and it's not "newer"
    ("2.3.0rc1", "2.2.0", False),     # pre-release string → never a nag
    ("garbage", "2.2.0", False),
    ("2.3.0", "not-a-version", False),
])
def test_is_newer(cand, cur, expected):
    assert uc._is_newer(cand, cur) is expected


# ── available_update ─────────────────────────────────────────────────────────

def test_opt_out_short_circuits_everything(monkeypatch, tmp_path):
    monkeypatch.setenv(uc.OPT_OUT_ENV, "1")
    monkeypatch.setattr(uc, "_CACHE_FILE", tmp_path / "x.json")
    called = []
    monkeypatch.setattr(uc, "_fetch_latest_from_pypi", lambda: called.append(1))
    assert uc.available_update() is None
    assert uc.get_meta_notice() == ""
    assert called == []  # no fetch, no thread


def test_fresh_cache_with_newer_version_reports_it(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    _write_cache(uc, "2.4.0")
    assert uc.available_update() == "2.4.0"


def test_fresh_cache_up_to_date_reports_nothing(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.4.0")
    _write_cache(uc, "2.4.0")
    assert uc.available_update() is None


def test_missing_cache_returns_none_and_warms_in_background(opted_in, monkeypatch):
    fake_fetch, calls = opted_in
    fake_fetch.result = "9.9.9"
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")

    assert uc.available_update() is None  # nothing to report yet

    # background thread should have run the fetch and written the cache
    for _ in range(50):
        if calls:
            break
        time.sleep(0.02)
    assert calls, "background refresh never fired"
    for _ in range(50):
        if uc._CACHE_FILE.exists():
            break
        time.sleep(0.02)
    assert json.loads(uc._CACHE_FILE.read_text())["latest"] == "9.9.9"


def test_stale_cache_is_ignored(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    _write_cache(uc, "5.0.0", age=uc._TTL + 100)
    assert uc.available_update() is None  # stale → not trusted


def test_background_refresh_only_starts_once(opted_in, monkeypatch):
    fake_fetch, calls = opted_in
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    for _ in range(5):
        uc.available_update()
    time.sleep(0.2)
    assert len(calls) <= 1


def test_corrupt_cache_file_does_not_raise(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    uc._CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    uc._CACHE_FILE.write_text("{ not json")
    assert uc.available_update() is None


# ── surfacing ────────────────────────────────────────────────────────────────

def test_startup_notice_prints_to_stderr_when_outdated(opted_in, monkeypatch, capsys):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    _write_cache(uc, "2.5.0")
    uc.startup_stderr_notice()
    err = capsys.readouterr().err
    assert "2.2.0 -> 2.5.0" in err
    assert "pip install -U lorcana-mcp" in err


def test_startup_notice_silent_when_current(opted_in, monkeypatch, capsys):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.5.0")
    _write_cache(uc, "2.5.0")
    uc.startup_stderr_notice()
    assert capsys.readouterr().err == ""


def test_get_meta_notice_shape_when_outdated(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    _write_cache(uc, "2.6.0")
    note = uc.get_meta_notice()
    assert note.startswith("\n\n---\n")
    assert "2.2.0 → 2.6.0" in note
    assert uc.OPT_OUT_ENV in note


def test_get_meta_tool_appends_notice(opted_in, monkeypatch):
    monkeypatch.setattr(uc, "installed_version", lambda: "2.2.0")
    _write_cache(uc, "2.6.0")
    from lorcana_mcp.server import get_meta
    out = get_meta()
    assert "not live data" in out          # the snapshot itself
    assert "newer **lorcana-mcp** is on PyPI" in out  # plus the notice
