"""Packaging checks: the package imports, the CLI is complete, the skill is named for its trigger."""

import re
from pathlib import Path

import agent_brainswarm
from agent_brainswarm import cli

REPO: Path = Path(__file__).resolve().parents[1]


def test_package_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", agent_brainswarm.__version__)


def test_cli_exposes_documented_subcommands() -> None:
    parser = cli.parser()
    sub = next(a for a in parser._actions if a.dest == "command")
    assert sub.choices is not None and set(cli.SUBCOMMANDS) <= set(sub.choices)


def test_skill_is_named_brainswarm() -> None:
    text = (REPO / ".claude/skills/brainswarm/SKILL.md").read_text()
    front = text.split("---")[1]
    assert "name: brainswarm" in front
    assert "brainstorm" in front  # description explicitly excludes it
