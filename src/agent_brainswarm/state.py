"""Run folder layout, atomic JSON I/O, and storage-location policy (DESIGN.md §11).

Layout of a run folder::

    <run>/
      config.json  status.json  brief.md
      rubric_draft.json  rubric.json  rubric.sha256
      tasks/<phase>/<dispatch>.md      what each agent is asked to do
      out/<phase>/<dispatch>.json      what each agent wrote
      data/*.json                      validated, code-produced state
      report.md  report.html  digest.txt  usage.json

Runs default to ``~/.agent-brainswarm/runs/`` (outside any repository, so
they cannot be committed by accident). ``BRAINSWARM_HOME`` overrides the
root, which the tests use.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

RUN_FILES = ("config.json", "status.json", "brief.md")
GITIGNORE_ENTRY = "brainswarm-state/"


def home() -> Path:
    """Root for runs and the idea library."""
    return Path(os.environ.get("BRAINSWARM_HOME", Path.home() / ".agent-brainswarm"))


def is_ephemeral() -> bool:
    """True in Claude Code on the web, where the home directory is reclaimed."""
    return os.environ.get("CLAUDE_CODE_REMOTE") == "true"


def new_run_id(seed: int, attempt: int = 0) -> str:
    """Timestamp plus 4 hex digits drawn from the run's seed and an attempt counter.

    Two runs with the same seed started in the same second would collide on
    attempt 0; callers retry with the next attempt until the folder is free.
    """
    suffix = int(np.random.default_rng([seed, attempt]).integers(16**4))
    return time.strftime("%Y%m%d-%H%M%S") + f"-{suffix:04x}"


def read_json(path: Path) -> Any:
    """Parse a JSON file."""
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    """Write JSON atomically (temp file + rename) so a crash never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def ensure_gitignored(project: Path, entry: str = GITIGNORE_ENTRY) -> bool:
    """Add ``entry`` to ``project/.gitignore`` if absent; return True if it was added."""
    path = project / ".gitignore"
    lines = path.read_text().splitlines() if path.exists() else []
    if entry in lines:
        return False
    path.write_text("\n".join([*lines, entry]) + "\n")
    return True


class Run:
    """Accessor for one run folder."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, *parts: str) -> Path:
        """Path inside the run folder."""
        return self.root.joinpath(*parts)

    def read(self, *parts: str) -> Any:
        """Read a JSON file inside the run."""
        return read_json(self.path(*parts))

    def write(self, data: Any, *parts: str) -> None:
        """Write a JSON file inside the run, atomically."""
        write_json(self.path(*parts), data)

    def exists(self, *parts: str) -> bool:
        """Whether a file exists inside the run."""
        return self.path(*parts).exists()

    @property
    def brief(self) -> str:
        """The user's brief."""
        return self.path("brief.md").read_text()

    @property
    def status(self) -> dict[str, Any]:
        """Mutable-by-copy view of status.json."""
        return dict(self.read("status.json"))

    def set_status(self, **changes: Any) -> None:
        """Update status.json fields."""
        status = self.status
        status.update(changes)
        self.write(status, "status.json")


def resolve_run(ref: str) -> Run:
    """Accept a run folder path or a run id under ``home()/runs``."""
    path = Path(ref)
    if (path / "status.json").exists():
        return Run(path)
    candidate = home() / "runs" / ref
    if (candidate / "status.json").exists():
        return Run(candidate)
    raise FileNotFoundError(f"no brainswarm run at {ref!r}")
