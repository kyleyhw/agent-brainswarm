"""Token calibration: projected new tokens per size preset from measured per-dispatch costs.

    uv run python docs/studies/token_calibration.py            # project (uses the JSON below)
    uv run python docs/studies/token_calibration.py --measure  # re-measure from local transcripts

Model. A run's new tokens are the sum over phases p of (dispatches in p) x (new tokens per
dispatch in p):

    T(size) = sum_p  n_p(size) * c_p

n_p(size) is counted exactly by driving a fixture-mode run (fake agents, zero tokens) at each
preset. c_p is measured from subagent transcripts of live runs (``--measure``) and stored in
``token_calibration_measured.json``. Phases never measured with web research on (research,
fact-check) and critique with web lookups use a low/high range instead of a point value; the
bounds and their sources are stated in ``ASSUMED`` below. The referee session is not counted.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MEASURED = HERE / "token_calibration_measured.json"
OUT = HERE / "token_calibration.json"
sys.path.insert(0, str(REPO))

# Recorded runs whose transcripts this session holds: run name -> recorded run folder (used to
# map legacy bare dispatch ids to phases).
RUNS = {
    "20260929-134819-36e5": REPO / "examples/demo-run",
}
BRIEF = "Come up with a stock trading strategy that trades on many days and optimises growth."

# (low, high) new tokens per dispatch, in thousands, for phases whose web-on cost has not been
# measured. Research and fact-check: design-session measurements of web-research subagents
# (DESIGN.md §6: ~50-120k new tokens each). Critique with web lookups: the web-off demo cost
# (measured) as the low bound, plus the same web-research allowance (+50k) as the high bound.
ASSUMED = {
    "research": (50.0, 120.0, "design-session web-research subagents"),
    "factcheck": (50.0, 120.0, "design-session web-research subagents"),
}
CRITIQUE_WEB_EXTRA = 50.0


def count_dispatches() -> dict[str, dict[str, int]]:
    """Dispatches per phase for each size preset (balanced exploration, web on)."""
    from agent_brainswarm import cli, pipeline
    from agent_brainswarm.config import build_config, config_to_dict
    from tests.fake_agents import rubric_draft, write_outputs

    home = Path(tempfile.mkdtemp(prefix="brainswarm-cal-"))
    os.environ["BRAINSWARM_HOME"] = str(home)
    counts: dict[str, dict[str, int]] = {}
    for size in ("quick", "standard", "deep"):
        config = config_to_dict(build_config(size, "balanced", {"draws": 50}, seed=1))
        run = cli.create_run(BRIEF, config, home / "runs", f"cal-{size}")  # own project each
        n: collections.Counter[str] = collections.Counter()
        while True:
            step = pipeline.next_step(run)
            if step["action"] == "done":
                break
            if step["action"] == "referee":
                if step["phase"] == "rubric":
                    run.write(rubric_draft(BRIEF), "rubric_draft.json")
                elif step["phase"] == "freeze":
                    pipeline.freeze(run)
                elif step["phase"] == "checkpoint":
                    pipeline.resume(run)
                continue
            n[step["phase"]] += len(step["dispatches"])
            write_outputs(run, step)
            pipeline.ingest(run)
        counts[size] = dict(n)
    return counts


def measure(extra_runs: dict[str, Path]) -> dict[str, Any]:
    """Per-phase new tokens per dispatch from local subagent transcripts."""
    from agent_brainswarm import usage

    per_phase: dict[str, list[float]] = collections.defaultdict(list)
    runs = {**RUNS, **extra_runs}
    for name, folder in runs.items():
        phases_of: dict[str, set[str]] = collections.defaultdict(set)
        for p in (folder / "out").glob("*/*.json"):
            phases_of[p.stem].add(p.parent.name)
        for key, paths in usage.find_run_transcripts(name).items():
            phase = key.split("/")[0] if "/" in key else "+".join(sorted(phases_of.get(key, {"?"})))
            for path in paths:
                per_phase[phase].append(usage.parse_transcript(path).new_tokens / 1000)
    return {
        "note": "new tokens per dispatch in thousands (uncached input + cache writes + output); "
        "'angles+ideate+research' pools generator dispatches whose phase the legacy "
        "descriptions did not record; all measured with web off",
        "runs": sorted(runs),
        "phases": {
            k: {
                "n": len(v),
                "mean_k": round(sum(v) / len(v), 1),
                "values_k": [round(x, 1) for x in v],
            }
            for k, v in sorted(per_phase.items())
        },
    }


def per_dispatch(measured: dict[str, Any]) -> dict[str, tuple[float, float]]:
    """(low, high) thousand new tokens per dispatch for every phase."""
    m = {k: v["mean_k"] for k, v in measured["phases"].items()}
    generator = m["angles+ideate+research"]
    cost = {phase: (m[phase], m[phase]) for phase in m if "+" not in phase}
    cost["angles"] = cost["ideate"] = (generator, generator)
    cost["critique"] = (m["critique"], m["critique"] + CRITIQUE_WEB_EXTRA)
    for phase, (low, high, _) in ASSUMED.items():
        cost[phase] = (low, high)
    cost.setdefault("boundary", cost["finals"])
    return cost


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--measure", nargs="*", metavar="RUN=FOLDER", help="re-measure")
    args = parser.parse_args()
    if args.measure is not None:
        extra = dict(item.split("=", 1) for item in args.measure)
        MEASURED.write_text(json.dumps(measure({k: Path(v) for k, v in extra.items()}), indent=2))
    measured = json.loads(MEASURED.read_text())
    cost = per_dispatch(measured)
    counts = count_dispatches()
    table: dict[str, Any] = {}
    for size, n in counts.items():
        low = sum(k * cost[p][0] for p, k in n.items()) / 1000
        high = sum(k * cost[p][1] for p, k in n.items()) / 1000
        table[size] = {
            "dispatches": sum(n.values()),
            "per_phase": n,
            "new_M": [round(low, 1), round(high, 1)],
        }
        print(f"{size:9s} {sum(n.values()):4d} dispatches   {low:5.1f}-{high:5.1f}M new tokens")
    OUT.write_text(
        json.dumps(
            {"cost_per_dispatch_k": {k: list(v) for k, v in cost.items()}, "presets": table},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
