"""Rebuild the demo reruns offline (zero tokens) and compare them with the recorded demo.

    uv run python examples/rerun_comparison.py [--figure docs/figures/position_bias.png]

Each branch is rebuilt with ``replay --until``: the recorded run is replayed up to the branch
point, then the committed new agent outputs in ``examples/demo-reruns/`` are fed through the
real code. Conditions:

* ``original``: the recorded demo (split judge schedule, first/second verdicts).
* ``finals-only``: same cards and schedule, new judge prompt (strengths of both ideas, a named
  winner, a cited criterion). Isolates the prompt change.
* ``crossover``: the finals-only verdicts plus each model re-judging the other orientation
  (24 verdicts; every model sees both orders of every pair).
* ``from-workshop``: workshop onward re-run with the word budget, new judge prompt and the
  crossover schedule (examples/demo-reruns/from-workshop/), if present.

For each condition the Bradley–Terry model with position bias is fitted and the position bias
gamma is reported with its 95 % Laplace interval, gamma_hat +/- 1.96 sqrt(Sigma_gamma,gamma).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from agent_brainswarm import cli
from agent_brainswarm.pipeline import ingest, next_step
from agent_brainswarm.scoring import PairEvent, fit
from agent_brainswarm.state import Run

HERE = Path(__file__).resolve().parent
RECORDED = HERE / "demo-run"
RERUNS = HERE / "demo-reruns"
Z95 = 1.959964  # two-sided 95 % normal quantile
PRIOR = 1.5  # the run's prior scale tau (config.json)


def branch(into: Path, name: str, until: str, design: str | None = None) -> Run:
    """Replay the recorded run to ``until``, then feed the committed outputs of ``name``."""
    run = cli.replay(RECORDED, into / name, until=until)
    if design:
        config = run.read("config.json")
        run.write({**config, "judge_design": design}, "config.json")
    source = RERUNS / name / "out"
    while True:
        step = next_step(run)
        if step["action"] == "done":
            return run
        for d in step["dispatches"]:
            src = source / step["phase"] / f"{d['id']}.json"
            dst = run.path("out", step["phase"], f"{d['id']}.json")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        ingest(run)


def events(matches: list[dict[str, Any]]) -> list[PairEvent]:
    return [
        PairEvent(m["first"], m["second"], m["preferred"] == "first", m["judge_id"])
        for m in matches
    ]


def summarise(name: str, ids: list[str], matches: list[dict[str, Any]]) -> dict[str, Any]:
    """First-listed wins and the fitted strengths and position bias with 95 % intervals."""
    f = fit(ids, events(matches), [], prior_scale=PRIOR)
    se = np.sqrt(np.diag(f.covariance))
    first = sum(m["preferred"] == "first" for m in matches)
    return {
        "condition": name,
        "first_wins": first,
        "verdicts": len(matches),
        "gamma": float(f.gamma),
        "gamma_ci": [float(f.gamma - Z95 * se[-1]), float(f.gamma + Z95 * se[-1])],
        "beta": {x: float(b) for x, b in zip(f.ids, f.beta, strict=True)},
        "beta_ci": {
            x: [float(b - Z95 * s), float(b + Z95 * s)]
            for x, b, s in zip(f.ids, f.beta, se[:-1], strict=True)
        },
        "rank": [x for _, x in sorted(zip(-f.beta, f.ids, strict=True))],
    }


def crossover_matches(finals_only: Run) -> list[dict[str, Any]]:
    """The finals-only verdicts plus the crossover verdicts, in Match form."""
    batches = {b["dispatch_id"]: b["pairs"] for b in finals_only.read("data", "judge_batches.json")}
    out = list(finals_only.read("data", "matches.json"))
    for path in sorted((RERUNS / "crossover").glob("finals-*.json")):
        dispatch, model = path.stem.rsplit("-", 1)
        for v in json.loads(path.read_text())["verdicts"]:
            a, b = batches[dispatch][int(v["pair_id"].rsplit("-", 1)[1]) - 1]
            out.append(
                {
                    "judge_id": f"{dispatch}-{model}",
                    "judge_model": model,
                    "first": a,
                    "second": b,
                    "preferred": "first" if v["winner"] == a else "second",
                }
            )
    return out


def flips(matches: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    """Per model: (pairs whose winner changed with the order, pairs seen in both orders)."""
    winners: dict[tuple[str, frozenset[str]], set[str]] = {}
    for m in matches:
        key = (m["judge_model"], frozenset((m["first"], m["second"])))
        winner = m["first"] if m["preferred"] == "first" else m["second"]
        winners.setdefault(key, set()).add(winner)
    out: dict[str, tuple[int, int]] = {}
    for (model, _), w in winners.items():
        changed, total = out.get(model, (0, 0))
        out[model] = (changed + (len(w) == 2), total + 1)
    return out


def figure(results: list[dict[str, Any]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, surface = "#1f1f1e", "#6b6a64", "#e4e3dc", "#fcfcfb"
    blue, orange = "#2a78d6", "#eb6834"  # reference categorical slots 1 and 2
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.3), facecolor=surface)
    for ax in (ax1, ax2):
        ax.set_facecolor(surface)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=9)
        ax.grid(axis="x", color=grid, linewidth=0.8)
        ax.set_axisbelow(True)

    labels = [
        f"{r['condition']}\n{r['first_wins']}/{r['verdicts']} first-listed wins" for r in results
    ]
    y = np.arange(len(results))[::-1]
    for yi, r in zip(y, results, strict=True):
        lo, hi = r["gamma_ci"]
        ax1.plot([lo, hi], [yi, yi], color=blue, linewidth=2, solid_capstyle="round")
        ax1.plot(
            r["gamma"],
            yi,
            "o",
            color=blue,
            markersize=8,
            markeredgecolor=surface,
            markeredgewidth=2,
        )
    ax1.axvline(0, color=muted, linewidth=1, linestyle="--")
    ax1.set_yticks(y, labels, color=ink, fontsize=8.5)
    ax1.set_xlabel("position bias γ (logits), 95 % interval", color=ink, fontsize=9)
    ax1.set_title("Bias toward the first-listed idea", color=ink, fontsize=10, loc="left")

    base, cross = results[0], next(r for r in results if r["condition"] == "crossover")
    ids = sorted(base["beta"], key=lambda x: -cross["beta"][x])
    yy = np.arange(len(ids))[::-1]
    for off, r, colour in ((0.14, base, orange), (-0.14, cross, blue)):
        for yi, x in zip(yy, ids, strict=True):
            lo, hi = r["beta_ci"][x]
            ax2.plot(
                [lo, hi], [yi + off, yi + off], color=colour, linewidth=2, solid_capstyle="round"
            )
            ax2.plot(
                r["beta"][x],
                yi + off,
                "o",
                color=colour,
                markersize=8,
                markeredgecolor=surface,
                markeredgewidth=2,
            )
    ax2.axvline(0, color=muted, linewidth=1, linestyle="--")
    ax2.set_yticks(yy, [x.removesuffix("-v2") for x in ids], color=ink, fontsize=9)
    ax2.set_xlabel("strength β (logits), 95 % interval", color=ink, fontsize=9)
    ax2.set_title("Finalist strengths", color=ink, fontsize=10, loc="left")
    handles = [
        plt.Line2D([], [], color=orange, marker="o", linewidth=2, label="original (12 verdicts)"),
        plt.Line2D([], [], color=blue, marker="o", linewidth=2, label="crossover (24 verdicts)"),
    ]
    ax2.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        labelcolor=ink,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.2),
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=surface)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", type=Path, help="write the comparison figure here")
    args = parser.parse_args()
    into = Path(tempfile.mkdtemp(prefix="brainswarm-reruns-"))
    os.environ.setdefault("BRAINSWARM_HOME", str(into / "home"))

    original = Run(RECORDED)
    ids = original.read("data", "finalists.json")
    finals_only = branch(into, "finals-only", "finals")
    results = [
        summarise("original", ids, original.read("data", "matches.json")),
        summarise("finals-only", ids, finals_only.read("data", "matches.json")),
    ]
    crossed = crossover_matches(finals_only)
    results.append(summarise("crossover", ids, crossed))
    if (RERUNS / "from-workshop").exists():
        workshop = branch(into, "from-workshop", "workshop", design="crossover")
        results.append(
            summarise(
                "from-workshop",
                workshop.read("data", "finalists.json"),
                workshop.read("data", "matches.json"),
            )
        )
        results[-1]["flips"] = flips(workshop.read("data", "matches.json"))
    results[2]["flips"] = flips(crossed)

    for r in results:
        lo, hi = r["gamma_ci"]
        print(
            f"{r['condition']:14s} first-listed wins {r['first_wins']:2d}/{r['verdicts']:2d}  "
            f"gamma {r['gamma']:5.2f} [{lo:5.2f}, {hi:5.2f}]  order {' > '.join(r['rank'])}"
            + (f"  flips {r['flips']}" if "flips" in r else "")
        )
    (RERUNS / "comparison.json").write_text(json.dumps(results, indent=2))
    if args.figure:
        figure(results, args.figure)
        print("figure:", args.figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
