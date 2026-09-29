"""Coverage study: do the finals' 95 % rank intervals contain the true rank 95 % of the time?

Simulates finals exactly as brainswarm schedules them (incomplete round robin,
both orders in different dispatches, <= 10 pairs per dispatch) from known
strengths, fits them with each uncertainty method, and counts how often the
true rank falls inside the reported 95 % rank interval.

Two scenarios:
  * independent: every verdict is an independent Bradley-Terry draw with
    position bias gamma;
  * correlated: each dispatch (one judge context) perturbs every idea's
    strength by its own N(0, 0.7^2) offset, so verdicts within a dispatch
    share an idiosyncratic view. This is the case the dispatch-level
    bootstrap exists for.

Run: uv run python docs/studies/uncertainty_coverage.py
Writes docs/studies/uncertainty_coverage.json and docs/figures/uncertainty_coverage.png.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from agent_brainswarm.schedule import judge_batches, match_pairs
from agent_brainswarm.scoring import PairEvent, ranks_of, score

HERE = Path(__file__).resolve().parent
FINALISTS = 12  # standard size: ~12 workshopped ideas reach the finals
MATCHES = 8  # standard finals_matches_per_idea
PER_DISPATCH = 10  # standard pairs_per_judge
GAMMA = 0.3  # a moderate first-position advantage, in logits
DISPATCH_SD = 0.7  # per-dispatch idiosyncrasy: ~half the spread of true strengths
REPLICATIONS = 40
DRAWS = 200


def simulate(
    rng: np.random.Generator, correlated: bool
) -> tuple[list[str], np.ndarray, list[PairEvent]]:
    ids = [f"F{i:02d}" for i in range(FINALISTS)]
    beta = rng.normal(size=FINALISTS)
    pairs = match_pairs(ids, MATCHES, rng)
    batches = judge_batches(pairs, PER_DISPATCH, ("opus", "fable", "sonnet"), rng)
    idx = {x: i for i, x in enumerate(ids)}
    events = []
    for b in batches:
        offset = (
            rng.normal(scale=DISPATCH_SD, size=FINALISTS) if correlated else np.zeros(FINALISTS)
        )
        for first, second in b.pairs:
            i, j = idx[first], idx[second]
            p = 1 / (1 + np.exp(-(beta[i] + offset[i] - beta[j] - offset[j] + GAMMA)))
            events.append(PairEvent(first, second, bool(rng.random() < p), b.dispatch_id))
    return ids, beta, events


def coverage(method: str, correlated: bool, seed: int) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    hits, widths = [], []
    for _ in range(REPLICATIONS):
        ids, beta, events = simulate(rng, correlated)
        forced = "laplace" if method == "Laplace" else "bootstrap"
        if method == "naive bootstrap":
            events = [
                PairEvent(e.first, e.second, e.first_won, f"e{k}") for k, e in enumerate(events)
            ]
        s = score(ids, pairs=events, draws=DRAWS, seed=int(rng.integers(2**31)), method=forced)
        truth = ranks_of(beta)
        for i, x in enumerate(ids):
            lo, hi = s.rank_interval[x]
            hits.append(lo <= truth[i] <= hi)
            widths.append(hi - lo + 1)
    return {"coverage": float(np.mean(hits)), "mean_width": float(np.mean(widths)), "n": len(hits)}


def main() -> None:
    start = time.perf_counter()
    methods = ["dispatch bootstrap", "naive bootstrap", "Laplace"]
    results: dict[str, object] = {
        scenario: {
            m: coverage(m, scenario == "correlated", seed=100 + k) for k, m in enumerate(methods)
        }
        for scenario in ("independent", "correlated")
    }
    results["runtime_s"] = round(time.perf_counter() - start, 1)
    (HERE / "uncertainty_coverage.json").write_text(json.dumps(results, indent=2))
    plot(results, methods)


def replot() -> None:
    """Redraw the figure from the saved results without re-simulating."""
    results = json.loads((HERE / "uncertainty_coverage.json").read_text())
    plot(results, ["dispatch bootstrap", "naive bootstrap", "Laplace"])
    print(json.dumps(results, indent=2))


def plot(results: dict, methods: list[str]) -> None:
    """Dot plot of coverage by method; dots (not bars) because the axis is zoomed."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted = "#fcfcfb", "#0b0b0b", "#52514e"
    colors = {"independent": "#2a78d6", "correlated": "#eb6834"}
    fig, ax = plt.subplots(figsize=(7, 3.4), dpi=150)
    fig.patch.set_facecolor(surface)
    ax.set_facecolor(surface)
    x = np.arange(len(methods))
    ax.axhline(0.95, color=muted, linestyle=(0, (4, 3)), linewidth=1, zorder=1)
    ax.text(-0.45, 0.951, "95% target", color=muted, ha="left", va="bottom", fontsize=8)
    for k, scenario in enumerate(("independent", "correlated")):
        vals = [results[scenario][m]["coverage"] for m in methods]
        ax.scatter(
            x + (k - 0.5) * 0.18,
            vals,
            s=64,
            color=colors[scenario],
            edgecolor=surface,
            linewidth=2,
            zorder=3,
            label=f"{scenario} judgments",
        )
    ax.set_xticks(x, methods, color=ink, fontsize=9)
    ax.set_xlim(-0.5, len(methods) - 0.5)
    ax.set_ylim(0.85, 1.0)
    ax.set_ylabel("Share of true ranks inside\nthe 95% rank interval", color=ink, fontsize=9)
    ax.tick_params(colors=muted, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(muted)
    ax.grid(axis="y", color="#e6e5e1", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.tight_layout()
    out = HERE.parent / "figures" / "uncertainty_coverage.png"
    fig.savefig(out, facecolor=surface)


if __name__ == "__main__":
    main()
