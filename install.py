#!/usr/bin/env python3
"""One-shot installer for agent-brainswarm.

Run from the repository root:

    uv run python install.py

What it does:

1. Installs the package as a uv tool (editable), so the ``brainswarm`` CLI,
   which the skill and the role guard hook call, is on PATH everywhere.
2. Symlinks ``.claude/skills/brainswarm`` into ``~/.claude/skills/`` and every
   ``.claude/agents/brainswarm-*.md`` into ``~/.claude/agents/``, so
   ``/brainswarm`` and its roles exist in every Claude Code session.

``--force`` replaces existing links; ``--skip-python`` / ``--skip-skills``
skip a step. Where symlinks are not permitted (e.g. Windows without
Developer Mode) files are copied instead, and later edits in the repository
will not propagate until the installer is re-run.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent


def claude_dir() -> Path:
    """User-level Claude Code configuration directory."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))


def link(src: Path, dst: Path, force: bool) -> str:
    """Symlink ``dst`` -> ``src`` (copy as fallback); return what happened."""
    if dst.is_symlink() or dst.exists():
        if dst.is_symlink() and dst.resolve() == src.resolve():
            return f"ok       {dst}"
        if not force:
            return f"skipped  {dst} (exists; use --force)"
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        dst.symlink_to(src, target_is_directory=src.is_dir())
        return f"linked   {dst}"
    except OSError:
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return f"copied   {dst} (symlink not permitted)"


def install_skills(force: bool) -> list[str]:
    """Link the skill folder and every role agent file into the user config."""
    home = claude_dir()
    lines = [link(REPO / ".claude/skills/brainswarm", home / "skills/brainswarm", force)]
    for agent in sorted((REPO / ".claude/agents").glob("brainswarm-*.md")):
        lines.append(link(agent, home / "agents" / agent.name, force))
    return lines


def install_python() -> int:
    """Install the CLI as an editable uv tool."""
    if not shutil.which("uv"):
        print("uv not found; install uv (https://docs.astral.sh/uv/) or run `pip install -e .`")
        return 1
    return subprocess.run(
        ["uv", "tool", "install", "--force", "--editable", str(REPO)], check=False
    ).returncode


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-python", action="store_true")
    parser.add_argument("--skip-skills", action="store_true")
    args = parser.parse_args(argv)
    code = 0
    if not args.skip_python:
        code = install_python()
    if not args.skip_skills:
        print("\n".join(install_skills(args.force)))
    return code


if __name__ == "__main__":
    sys.exit(main())
