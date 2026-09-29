"""Token accounting from Claude Code transcripts (DESIGN.md §14).

Every dispatch is launched with the description ``bs <run> <phase>/<dispatch>``,
which Claude Code stores in ``<projects>/<slug>/<session>/subagents/
agent-<id>.meta.json`` next to the transcript ``agent-<id>.jsonl``. This
module finds a run's subagent transcripts that way and sums their usage.

Findings from the design session (tests/reports/2026-09-29_platform.md):

* Streaming writes several entries per message; entries are deduplicated by
  message id, keeping the maximum of each field.
* Input and cache fields are logged when a request starts and are reliable.
* Subagent transcripts almost never contain a message's *final* usage
  entry (``stop_reason`` set), so ``output_tokens`` there is a large
  undercount. For messages without a final entry the output is estimated
  as characters / 4 (a common English-text rule of thumb) and labelled as
  an estimate. Thinking content is not always stored, so the estimate is a
  lower bound.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

CHARS_PER_TOKEN = 4


@dataclass
class Usage:
    """Token counts for one or more agents."""

    input: int = 0
    cache_write: int = 0
    cache_read: int = 0
    output_logged: int = 0
    output_estimated: int = 0
    messages: int = 0
    messages_without_final_usage: int = 0
    agents: list[str] = field(default_factory=list)

    @property
    def new_tokens(self) -> int:
        """Uncached input + cache writes + best output figure."""
        return self.input + self.cache_write + max(self.output_logged, self.output_estimated)

    def add(self, other: Usage) -> None:
        """Accumulate another agent's usage."""
        for name in ("input", "cache_write", "cache_read", "output_logged", "output_estimated"):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        self.messages += other.messages
        self.messages_without_final_usage += other.messages_without_final_usage
        self.agents += other.agents


def projects_dir() -> Path:
    """Where Claude Code keeps transcripts."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"


def parse_transcript(path: Path) -> Usage:
    """Usage for one transcript file."""
    per_message: dict[str, dict[str, int]] = {}
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = row.get("message")
        if not isinstance(msg, dict) or not msg.get("usage") or not msg.get("id"):
            continue
        u = msg["usage"]
        entry = per_message.setdefault(
            msg["id"], {"input": 0, "cw": 0, "cr": 0, "out": 0, "final": 0, "chars": 0}
        )
        entry["input"] = max(entry["input"], int(u.get("input_tokens") or 0))
        entry["cw"] = max(entry["cw"], int(u.get("cache_creation_input_tokens") or 0))
        entry["cr"] = max(entry["cr"], int(u.get("cache_read_input_tokens") or 0))
        entry["out"] = max(entry["out"], int(u.get("output_tokens") or 0))
        entry["final"] |= int(msg.get("stop_reason") is not None)
        for block in msg.get("content", []):
            if isinstance(block, dict):
                text = (
                    block.get("text") or block.get("thinking") or json.dumps(block.get("input", ""))
                )
                entry["chars"] += len(text)
    usage = Usage(agents=[path.stem])
    for e in per_message.values():
        usage.input += e["input"]
        usage.cache_write += e["cw"]
        usage.cache_read += e["cr"]
        usage.messages += 1
        if e["final"]:
            usage.output_logged += e["out"]
            usage.output_estimated += e["out"]
        else:
            usage.messages_without_final_usage += 1
            usage.output_logged += e["out"]
            usage.output_estimated += max(e["out"], e["chars"] // CHARS_PER_TOKEN)
    return usage


def find_run_transcripts(run_name: str, root: Path | None = None) -> dict[str, list[Path]]:
    """Map dispatch key -> transcript paths for subagents launched for this run.

    The key is ``<phase>/<id>`` (descriptions ``bs <run> <phase>/<id>``) or, for runs
    recorded before phases were added, the bare id. It maps to a list because a retried
    dispatch reuses its description, and every attempt costs tokens.
    """
    found: dict[str, list[Path]] = {}
    marker = f"bs {run_name} "
    for meta in (root or projects_dir()).glob("*/*/subagents/*.meta.json"):
        try:
            description = str(json.loads(meta.read_text()).get("description", ""))
        except (json.JSONDecodeError, OSError):
            continue
        if description.startswith(marker):
            transcript = meta.with_name(meta.name.replace(".meta.json", ".jsonl"))
            if transcript.exists():
                found.setdefault(description[len(marker) :].strip(), []).append(transcript)
    return found


def summarise(paths: Iterable[Path]) -> Usage:
    """Total usage over transcripts."""
    total = Usage()
    for p in paths:
        total.add(parse_transcript(p))
    return total
