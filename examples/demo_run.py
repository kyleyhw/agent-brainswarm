"""Offline brainswarm demo: replay a recorded run through the real code, zero tokens.

    uv run python examples/demo_run.py [--into DIR]

`examples/demo-run/` holds the agent outputs (`out/`), rubric, brief and
config of a real live run (see examples/README.md). This script creates a
fresh run folder, feeds it the recorded outputs dispatch by dispatch, and
lets the code do everything else: rubric freeze and hash check, slot
assignment, critique checks, the substitution-test merge, the preliminary
and final fits, gates, workshop slots, the finals schedule, the report, and
the idea library. The ranking must reproduce the recorded one exactly.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from agent_brainswarm.cli import replay

HERE = Path(__file__).resolve().parent
RECORDED = HERE / "demo-run"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--into", help="where to write the replayed run (default: a temp folder)")
    args = parser.parse_args()
    into = Path(args.into) if args.into else Path(tempfile.mkdtemp(prefix="brainswarm-replay-"))
    run = replay(RECORDED, into)
    print(run.path("digest.txt").read_text())
    recorded = json.loads((RECORDED / "data" / "final.json").read_text())["rank"]
    replayed = run.read("data", "final.json")["rank"]
    print("ranking reproduced exactly:", recorded == replayed)
    print("full report:", run.path("report.html"))
    return 0 if recorded == replayed else 1


if __name__ == "__main__":
    raise SystemExit(main())
