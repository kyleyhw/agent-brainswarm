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


def test_skill_is_named_brainswarm_and_parses() -> None:
    import yaml

    text = (REPO / ".claude/skills/brainswarm/SKILL.md").read_text()
    front = yaml.safe_load(text.split("---")[1])
    assert front["name"] == "brainswarm"
    assert "brainstorm" in front["description"]  # description explicitly excludes it


def test_every_dispatched_role_has_a_guarded_agent_definition() -> None:
    import yaml

    source = (REPO / "src/agent_brainswarm/pipeline.py").read_text()
    roles = set(re.findall(r'_dispatch\(\s*run,\s*[^,]+,\s*[^,]+,\s*"([a-z-]+)"', source))
    assert {"ideator", "generator", "clusterer", "critic", "judge", "workshop"} <= roles
    for role in roles:
        text = (REPO / f".claude/agents/brainswarm-{role}.md").read_text()
        front = yaml.safe_load(text.split("---")[1])
        assert front["name"] == f"brainswarm-{role}"
        assert front["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "brainswarm guard"
        if role in ("clusterer", "checker", "advocate", "judge", "rubric-auditor", "ideator"):
            assert "Web" not in front["tools"] and "Bash" not in front["tools"]
