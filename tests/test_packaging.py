"""Packaging checks: the package imports, the CLI is complete, the skill is named for its trigger."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

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
        text = (REPO / f"agents/brainswarm-{role}.md").read_text()
        front = yaml.safe_load(text.split("---")[1])
        assert front["name"] == f"brainswarm-{role}"
        assert front["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == hook_command()
        if role in ("clusterer", "checker", "advocate", "judge", "rubric-auditor", "ideator"):
            assert "Web" not in front["tools"] and "Bash" not in front["tools"]


def test_installer_links_skill_and_agents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("install", REPO / "install.py")
    assert spec and spec.loader
    install = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(install)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert install.main(["--skip-python"]) == 0
    assert (tmp_path / "skills/brainswarm/SKILL.md").exists()
    agents = sorted(p.name for p in (tmp_path / "agents").iterdir())
    assert "brainswarm-judge.md" in agents and len(agents) == 9
    # Re-running is idempotent.
    assert all(line.startswith("ok") for line in install.install_skills(force=False))


def hook_command() -> str:
    """The guard hook command shared by every role agent."""
    text = (REPO / "agents/brainswarm-judge.md").read_text()
    front = yaml.safe_load(text.split("---")[1])
    return front["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


@pytest.mark.parametrize("on_path", [True, False])
def test_guard_hook_fails_closed(tmp_path: Path, on_path: bool) -> None:
    # Claude Code blocks only on exit 2; a missing CLI (exit 127) would silently allow.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    if on_path:
        fake = bin_dir / "brainswarm"
        fake.write_text("#!/bin/sh\necho guard-ran\nexit 0\n")
        fake.chmod(0o755)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
    done = subprocess.run(
        ["sh", "-c", hook_command()],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if on_path:
        assert done.returncode == 0 and "guard-ran" in done.stdout
    else:
        assert done.returncode == 2 and "not on PATH" in done.stderr
