"""Shared fixtures: isolate BRAINSWARM_HOME and Claude transcript lookups per test."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "bs-home"
    monkeypatch.setenv("BRAINSWARM_HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    return home
