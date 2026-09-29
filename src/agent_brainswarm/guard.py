"""PreToolUse guard for brainswarm roles (declared in the role agents' frontmatter).

Claude Code passes the pending tool call as JSON on stdin. Exit code 0
allows it; exit code 2 blocks it and shows stderr to the agent.

Rules:

* **Bash**: only ``brainswarm sandbox run ...`` (scratch code runs in the
  network-less container, never on the host). A command containing shell
  control operators is refused so the allowed prefix cannot smuggle a
  second command.
* **Write / Edit**: only JSON files under a run's ``out/`` folder, or files
  under a ``sandbox-scratch`` folder.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import PurePath
from typing import Any

ALLOWED_BASH = re.compile(r"^\s*(uv run\s+)?brainswarm sandbox run\s")
CONTROL = re.compile(r"[;&|`$<>]|\n")


def decide(call: dict[str, Any]) -> tuple[bool, str]:
    """Return (allowed, reason) for one tool call."""
    tool = call.get("tool_name", "")
    args = call.get("tool_input", {}) or {}
    if tool == "Bash":
        command = str(args.get("command", ""))
        if ALLOWED_BASH.match(command) and not CONTROL.search(command):
            return True, ""
        return False, "brainswarm roles may only run `brainswarm sandbox run <script.py>`"
    if tool in ("Write", "Edit", "MultiEdit"):
        parts = PurePath(str(args.get("file_path", ""))).parts
        in_out = "out" in parts and str(args.get("file_path", "")).endswith(".json")
        in_scratch = "sandbox-scratch" in parts
        if (in_out or in_scratch) and ".." not in parts:
            return True, ""
        return (
            False,
            "brainswarm roles may only write their output JSON under the run's out/ folder",
        )
    return True, ""


def main() -> int:
    """Hook entry point."""
    try:
        call = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print("guard: unreadable hook input", file=sys.stderr)
        return 2
    allowed, reason = decide(call)
    if not allowed:
        print(reason, file=sys.stderr)
        return 2
    return 0
