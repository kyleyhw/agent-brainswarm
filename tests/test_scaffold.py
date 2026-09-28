"""Scaffold checks: the package imports and the skill is named for its trigger."""

from pathlib import Path

import agent_brainswarm
from agent_brainswarm import cli

REPO = Path(__file__).resolve().parents[1]


def test_package_imports():
    assert agent_brainswarm.__version__


def test_cli_reports_not_implemented():
    assert cli.main(["validate"]) == 1


def test_skill_is_named_brainswarm():
    text = (REPO / ".claude/skills/brainswarm/SKILL.md").read_text()
    front = text.split("---")[1]
    assert "name: brainswarm" in front
    assert "brainstorm" in front  # description explicitly excludes it
