"""Shared test fixtures."""
from __future__ import annotations

import pytest

from lorcana_mcp import update_check


@pytest.fixture(autouse=True)
def _no_update_check(monkeypatch):
    """Disable the PyPI update check for every test by default.

    It is opt-out via an env var, and opting out short-circuits before any
    cache read, thread spawn, or network call — so no test accidentally
    fetches from pypi.org or leaves a background thread running.
    `test_update_check.py` opts back in explicitly where it needs to.
    """
    monkeypatch.setenv(update_check.OPT_OUT_ENV, "1")
