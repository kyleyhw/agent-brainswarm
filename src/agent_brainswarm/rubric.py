"""Rubric freeze and hash check (DESIGN.md §4, directive 2).

The rubric is serialised canonically (sorted keys, no insignificant
whitespace) and hashed with SHA-256 before any agent is dispatched. Every
later phase that judges ideas calls :func:`verify`, which refuses to proceed
if the rubric on disk no longer matches the recorded hash. This makes
"the rubric is frozen before dispatch" a property of the code, not a promise
in a prompt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from agent_brainswarm.models import Rubric, SchemaError, dump, load

RUBRIC_FILE = "rubric.json"
HASH_FILE = "rubric.sha256"
LEGALITY_GATE = "legal_and_ethical"


class RubricChangedError(RuntimeError):
    """The rubric on disk differs from the one frozen at dispatch."""


def canonical(rubric: Rubric) -> str:
    """Canonical JSON text of a rubric; identical rubrics give identical text."""
    return json.dumps(dump(rubric), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(rubric: Rubric) -> str:
    """SHA-256 hex digest of the canonical rubric."""
    return hashlib.sha256(canonical(rubric).encode()).hexdigest()


def check_rubric(rubric: Rubric) -> None:
    """Structural rules the referee's draft must satisfy before freezing."""
    problems: list[str] = []
    names = [c.name for c in rubric.criteria]
    if len(names) != len(set(names)):
        problems.append("criterion names must be unique")
    if LEGALITY_GATE not in names:
        problems.append(f"the default gate '{LEGALITY_GATE}' is required (DESIGN.md §5)")
    if not any(c.kind == "judged" for c in rubric.criteria):
        problems.append("at least one judged criterion is required")
    for c in rubric.criteria:
        if c.kind == "gate" and not c.user_stated and c.name != LEGALITY_GATE:
            problems.append(
                f"gate '{c.name}' was not stated by the user; inferred constraints must be "
                "judged criteria, not gates (rank, don't remove)"
            )
        if c.kind == "measured" and not c.command:
            problems.append(f"measured criterion '{c.name}' needs a command")
    if problems:
        raise SchemaError(problems)


def freeze(rubric: Rubric, run_dir: Path) -> str:
    """Validate, write, and hash the rubric; return the hash."""
    check_rubric(rubric)
    (run_dir / RUBRIC_FILE).write_text(json.dumps(dump(rubric), indent=2, ensure_ascii=False))
    value = digest(rubric)
    (run_dir / HASH_FILE).write_text(value + "\n")
    return value


def verify(run_dir: Path) -> Rubric:
    """Load the rubric and confirm it still matches the frozen hash."""
    rubric = load(Rubric, json.loads((run_dir / RUBRIC_FILE).read_text()))
    expected = (run_dir / HASH_FILE).read_text().strip()
    if digest(rubric) != expected:
        raise RubricChangedError(
            "rubric.json changed after it was frozen; judging refuses to continue "
            "(never re-judge against a different rubric)"
        )
    return rubric
