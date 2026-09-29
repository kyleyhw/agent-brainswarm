"""Independent LLM reviewers for a benchmark pack, with order counterbalancing.

    uv run python benchmark/llm_review.py make <run> <baseline.json> <out-dir>
        [--models sonnet opus fable] [--k 3] [--reviewers 6] [--criteria criteria.json]
    uv run python benchmark/llm_review.py analyze <out-dir> [--figure path.png]

``make`` writes one task per reviewer, with brainswarm's top ``k`` cards (by its own final rank)
and the single agent's top 3. Reviewer r sees the cards in the order of row r of a cyclic Latin
square over a random base permutation, so no card appears twice in the same position, and with
as many reviewers as cards every card appears exactly once in every position; letters follow
the presented order, so "A" names a different card for each reviewer. The key (reviewer -> letter -> origin) and the seed, drawn
from OS entropy by numpy, go to ``key.json``.

``analyze`` reads the reviewers' JSON and reports, per reviewer r, the difference

    d_r = mean_{x in S} q_r(x) - mean_{x in B} q_r(x)

between the brainswarm (S) and single-agent (B) cards for the "would pursue" score and for rank,
an exact two-sided sign test on the d_r, Kendall's W for agreement between reviewers,

    W = 12 S / (m^2 (n^3 - n)),   S = sum_i (R_i - mean R)^2,

with m reviewers, n cards and R_i the rank sum of card i, and the Spearman correlation between
presented position and rank (a position-bias check that the Latin square makes unconfounded).
"""

from __future__ import annotations

import argparse
import json
import math
import string
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_pack import brainswarm_top, leaks, render

# Default criteria: the ETF brief's. Other briefs pass --criteria (a JSON list of
# {"name", "text"}); every list must include "pursue", the benchmark's headline measure.
ETF_CRITERIA = [
    {
        "name": "constraints",
        "text": "how convincingly it meets the brief's hard rules: trading days, turnover, daily closes, long only",
    },
    {
        "name": "drawdown",
        "text": "how credible its case for staying under a 20 % maximum drawdown is",
    },
    {"name": "growth", "text": "long-run growth potential"},
    {"name": "diversification", "text": "spread of risk across asset classes"},
    {"name": "pursue", "text": "would a quantitative researcher spend a week testing it?"},
]


def task_text(brief: str, cards: list[str], out: Path, criteria: list[dict[str, str]]) -> str:
    letters = string.ascii_uppercase[: len(cards)]
    names = [c["name"] for c in criteria]
    example = {
        x: {**dict.fromkeys(names, 3), "rank": i + 1, "reason": "one sentence"}
        for i, x in enumerate(letters[:2])
    }
    listed = ", ".join(f"`{c['name']}` ({c['text']})" for c in criteria)
    return "\n".join(
        [
            "# Idea review task",
            "",
            (
                "This is a rating task, not a pairwise match: rate every idea on its own, then rank "
                "them. Read no file other than this one."
            ),
            "",
            "## Brief",
            "",
            brief,
            "",
            "## How to rate",
            "",
            (
                f"Score each idea from 1 (poor) to 5 (excellent) on: {listed}. Then give every idea "
                f"a distinct `rank` from 1 (best) to {len(cards)}. Judge substance: mechanism, "
                "evidence, and whether the rules are really met. Do not reward length, jargon, or "
                "confident tone. The order of the ideas is random and carries no information. Do "
                "not guess who wrote them."
            ),
            "",
            "## Ideas",
            "",
            *cards,
            "",
            "## Output",
            "",
            (
                f"Write one JSON object to `{out}` with an entry for every idea "
                f"({', '.join(letters)}), for example:"
            ),
            "",
            "```json",
            json.dumps({"ratings": example}),
            "```",
        ]
    )


def make(
    run: Path,
    baseline: Path,
    out: Path,
    models: list[str],
    k: int = 3,
    reviewers: int | None = None,
    criteria_path: Path | None = None,
) -> int:
    criteria = json.loads(criteria_path.read_text()) if criteria_path else ETF_CRITERIA
    assert any(c["name"] == "pursue" for c in criteria), "criteria must include 'pursue'"
    top = json.loads(baseline.read_text())["top3"]
    entries = brainswarm_top(run, k) + [
        {**c, "origin": f"single agent #{i + 1}"} for i, c in enumerate(top)
    ]
    if any(leaks(e) for e in entries):
        print("refusing: a card refers to another idea by number or id")
        return 1
    n = len(entries)
    entropy = np.random.SeedSequence().entropy
    assert isinstance(entropy, int)
    base = np.random.default_rng(entropy).permutation(n)
    brief = (run / "brief.md").read_text().strip()
    key: dict[str, Any] = {
        "seed": entropy,
        "criteria": [c["name"] for c in criteria],
        # brainswarm's own final order, so analysis can compare its top 3 with the baseline's
        "brainswarm_order": [e["origin"] for e in entries if e["origin"].startswith("brainswarm")],
        "reviewers": {},
    }
    (out / "tasks").mkdir(parents=True, exist_ok=True)
    (out / "out").mkdir(parents=True, exist_ok=True)
    for r in range(reviewers or n):
        order = [int(base[(r + j) % n]) for j in range(n)]  # cyclic Latin square row
        letters = string.ascii_uppercase[:n]
        cards = [render(letters[j], entries[i]) for j, i in enumerate(order)]
        rid = f"r{r + 1}"
        target = (out / "out" / f"{rid}.json").resolve()
        (out / "tasks" / f"{rid}.md").write_text(task_text(brief, cards, target, criteria))
        key["reviewers"][rid] = {
            "model": models[r % len(models)],
            "labels": {letters[j]: entries[i]["origin"] for j, i in enumerate(order)},
        }
    (out / "key.json").write_text(json.dumps(key, indent=2))
    for rid, v in key["reviewers"].items():
        print(rid, v["model"], (out / "tasks" / f"{rid}.md").resolve())
    return 0


def sign_test(diffs: list[float]) -> float:
    """Exact two-sided sign test p-value, ties dropped."""
    pos, neg = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    k, m = min(pos, neg), pos + neg
    if m == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2**m)


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def analyze(out: Path, figure: Path | None) -> int:
    key = json.loads((out / "key.json").read_text())
    crit = tuple(key.get("criteria", [c["name"] for c in ETF_CRITERIA]))
    rows: list[dict[str, Any]] = []
    for rid, info in key["reviewers"].items():
        data = json.loads((out / "out" / f"{rid}.json").read_text())["ratings"]
        for position, (letter, origin) in enumerate(info["labels"].items(), start=1):
            rows.append(
                {"reviewer": rid, "model": info["model"], "origin": origin, "position": position}
                | {c: data[letter][c] for c in (*crit, "rank")}
            )
    origins = sorted({r["origin"] for r in rows})
    side = {o: ("brainswarm" if o.startswith("brainswarm") else "single agent") for o in origins}
    reviewers = list(key["reviewers"])
    result: dict[str, Any] = {"per_idea": {}, "per_reviewer": {}, "tests": {}}
    for o in origins:
        mine = [r for r in rows if r["origin"] == o]
        result["per_idea"][o] = {
            "side": side[o],
            **{c: float(np.mean([r[c] for r in mine])) for c in (*crit, "rank")},
            "ranks": [r["rank"] for r in mine],
        }
    # Compare brainswarm's own top 3 with the baseline's 3 (the benchmark question), whatever
    # number of brainswarm cards the reviewers saw.
    own_top = set(key.get("brainswarm_order", [o for o in origins if side[o] == "brainswarm"])[:3])
    for measure in ("pursue", "rank"):
        diffs = []
        for rid in reviewers:
            mine = [r for r in rows if r["reviewer"] == rid]
            s = np.mean([r[measure] for r in mine if r["origin"] in own_top])
            b = np.mean([r[measure] for r in mine if side[r["origin"]] == "single agent"])
            diffs.append(float(s - b))
            result["per_reviewer"].setdefault(rid, {})[f"{measure}_diff"] = float(s - b)
        result["tests"][measure] = {
            "mean_diff": float(np.mean(diffs)),
            "reviewers_favouring_brainswarm": sum(
                (d > 0) if measure == "pursue" else (d < 0) for d in diffs
            ),
            "sign_test_p": sign_test(diffs),
        }
    m, n = len(reviewers), len(origins)
    rank_sums = np.array([sum(result["per_idea"][o]["ranks"]) for o in origins], dtype=float)
    s_dev = float(((rank_sums - rank_sums.mean()) ** 2).sum())
    result["tests"]["kendall_w"] = 12 * s_dev / (m**2 * (n**3 - n))
    result["tests"]["position_rank_spearman"] = spearman(
        [r["position"] for r in rows], [r["rank"] for r in rows]
    )
    (out / "results.json").write_text(json.dumps(result, indent=2))
    for o in sorted(origins, key=lambda x: result["per_idea"][x]["rank"]):
        v = result["per_idea"][o]
        print(
            f"{o:24s} {v['side']:13s} mean rank {v['rank']:.2f}  pursue {v['pursue']:.2f}  ranks {v['ranks']}"
        )
    print(json.dumps(result["tests"], indent=2))
    if figure:
        plot(result, figure)
    return 0


def plot(result: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, surface = "#1f1f1e", "#6b6a64", "#e4e3dc", "#fcfcfb"
    colour = {"brainswarm": "#2a78d6", "single agent": "#eb6834"}  # categorical slots 1, 2
    ideas = sorted(result["per_idea"], key=lambda x: -result["per_idea"][x]["rank"])
    fig, ax = plt.subplots(figsize=(8, 3.8), facecolor=surface)
    ax.set_facecolor(surface)
    for y, o in enumerate(ideas):
        v = result["per_idea"][o]
        c = colour[v["side"]]
        jitter = np.linspace(-0.18, 0.18, len(v["ranks"]))
        ax.scatter(v["ranks"], y + jitter, s=22, color=c, alpha=0.45, linewidths=0)
        ax.plot(
            v["rank"], y, "o", color=c, markersize=10, markeredgecolor=surface, markeredgewidth=2
        )
    ax.set_yticks(range(len(ideas)), ideas, color=ink, fontsize=9)
    n = len(ideas)
    ax.set_xticks(range(1, n + 1))
    ax.set_xlim(0.6, n + 0.4)
    ax.invert_xaxis()
    ax.set_xlabel(f"rank given by each reviewer ({n} = worst, 1 = best)", color=ink, fontsize=9)
    ax.grid(axis="x", color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(grid)
    ax.tick_params(colors=muted, labelsize=9)
    handles = [
        plt.Line2D([], [], color=c, marker="o", linestyle="", label=k) for k, c in colour.items()
    ]
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        labelcolor=ink,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
    )
    ax.set_title(
        f"Ranks from {len(next(iter(result['per_idea'].values()))['ranks'])} independent reviewers",
        color=ink,
        fontsize=10,
        loc="left",
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=surface)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("make")
    s.add_argument("run", type=Path)
    s.add_argument("baseline", type=Path)
    s.add_argument("out", type=Path)
    s.add_argument("--models", nargs="+", default=["sonnet", "opus", "fable"])
    s.add_argument("--k", type=int, default=3, help="brainswarm cards shown (its top k)")
    s.add_argument("--reviewers", type=int, help="default: one per card (full Latin square)")
    s.add_argument("--criteria", type=Path, help="JSON list of {name, text}; default: ETF")
    s = sub.add_parser("analyze")
    s.add_argument("out", type=Path)
    s.add_argument("--figure", type=Path)
    args = parser.parse_args()
    if args.command == "make":
        return make(
            args.run, args.baseline, args.out, args.models, args.k, args.reviewers, args.criteria
        )
    return analyze(args.out, args.figure)


if __name__ == "__main__":
    raise SystemExit(main())
