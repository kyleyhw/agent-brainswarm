"""Stage 1 experiment: do alternative top-3 selection rules pick better ideas? (zero tokens)

    uv run python benchmark/experiments/selection_rules.py

Tests two ideas from the self-run (examples/runs/2026-09-29-beat-baseline) offline, on its saved
finals verdicts, against an external quality measure: the blinded reviewer panel's mean
"would pursue" score q_i for each of its 8 finalists (benchmark/beat-baseline/llm-review).

Rules compared (each picks 3 of the 8 finalists from the run's own verdicts only):

* ``current``: the 3 highest posterior-mode strengths beta_i (what brainswarm reports).
* ``portfolio`` (idea I003): the set S maximising the posterior expected best strength,
  E[max_{i in S} beta_i], estimated from draws theta ~ N(theta_hat, Sigma) of the Laplace
  approximation. Uncertain ideas gain from this: a set containing one of them has a better
  chance that its best member is truly strong.
* ``reliability`` (idea I008): refit Bradley-Terry with each verdict weighted by its judge
  model's reliability w_m = max(0, 2 a_m - 1), where a_m is the share of that model's verdicts
  that agreed with the panel on the *other* brief (ETF), so the rule is not graded on the
  data it was fitted to. A model unseen there gets the mean weight of the seen models.

Scores per rule: best-of-3 and mean-of-3 q, against the oracle (the 3 highest q) and the mean
over all C(8,3) = 56 possible sets (what a random choice would give).
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO = Path(__file__).resolve().parents[2]
from agent_brainswarm.scoring import PairEvent, fit

RUN = REPO / "examples/runs/2026-09-29-beat-baseline"
PANEL = REPO / "benchmark/beat-baseline/llm-review"
ETF_RUN = REPO / "examples/demo-run"
ETF_PANEL = REPO / "benchmark/etf-strategy/llm-review"
ETF_RERUNS = REPO / "examples/demo-reruns"  # finals-only and crossover verdicts, same cards
PRIOR = 1.5  # the runs' prior scale tau (config.json)
DRAWS = 20000  # posterior draws for E[max]; Monte Carlo error on the estimate is ~0.01


def matches(run: Path) -> list[dict[str, Any]]:
    return json.loads((run / "data" / "matches.json").read_text())


def panel_quality(panel: Path) -> dict[str, float]:
    """Mean 'pursue' per brainswarm card, keyed by idea id without the version suffix."""
    per = json.loads((panel / "results.json").read_text())["per_idea"]
    return {
        o.split()[1].split("-")[0]: v["pursue"]
        for o, v in per.items()
        if o.startswith("brainswarm")
    }


def model_agreement() -> dict[str, float]:
    """Share of each judge model's ETF verdicts that agree with the ETF panel's mean rank."""
    per = json.loads((ETF_PANEL / "results.json").read_text())["per_idea"]
    rank = {o.split()[1]: v["rank"] for o, v in per.items() if o.startswith("brainswarm")}
    # The recorded finals plus the finals-only rerun and the crossover, which judged the same
    # cards (the from-workshop rerun developed new cards, so it is excluded).
    verdicts = list(matches(ETF_RUN))
    batches = {
        b["dispatch_id"]: b["pairs"]
        for b in json.loads((ETF_RUN / "data" / "judge_batches.json").read_text())
    }
    extra = [
        (ETF_RERUNS / "finals-only/out/finals/finals-001.json", "finals-001", "sonnet"),
        (ETF_RERUNS / "finals-only/out/finals/finals-002.json", "finals-002", "opus"),
        (ETF_RERUNS / "crossover/finals-001-opus.json", "finals-001", "opus"),
        (ETF_RERUNS / "crossover/finals-002-sonnet.json", "finals-002", "sonnet"),
    ]
    for path, dispatch, model in extra:
        for v in json.loads(path.read_text())["verdicts"]:
            a, b = batches[dispatch][int(v["pair_id"].rsplit("-", 1)[1]) - 1]
            verdicts.append(
                {
                    "first": a,
                    "second": b,
                    "judge_model": model,
                    "preferred": "first" if v["winner"] == a else "second",
                }
            )
    agree: dict[str, list[bool]] = {}
    for m in verdicts:
        a, b = m["first"], m["second"]
        if a in rank and b in rank:
            winner = a if m["preferred"] == "first" else b
            loser = b if winner == a else a
            agree.setdefault(m["judge_model"], []).append(rank[winner] < rank[loser])
    return {k: float(np.mean(v)) for k, v in agree.items()}


def weighted_fit(
    ids: list[str], ms: list[dict[str, Any]], w: dict[str, float]
) -> NDArray[np.float64]:
    """MAP Bradley-Terry strengths with position bias, each verdict weighted by its model."""
    idx = {x: i for i, x in enumerate(ids)}
    n = len(ids)
    theta = np.zeros(n + 1)  # strengths, then gamma
    for _ in range(100):
        grad = -theta / PRIOR**2
        hess = -np.eye(n + 1) / PRIOR**2
        for m in ms:
            wt = w[m["judge_model"]]
            if wt == 0:
                continue
            f, s = idx[m["first"]], idx[m["second"]]
            x = np.zeros(n + 1)
            x[f], x[s], x[n] = 1.0, -1.0, 1.0
            p = 1 / (1 + np.exp(-x @ theta))
            y = 1.0 if m["preferred"] == "first" else 0.0
            grad += wt * (y - p) * x
            hess -= wt * p * (1 - p) * np.outer(x, x)
        step = np.linalg.solve(hess, grad)
        theta -= step
        if np.abs(step).max() < 1e-10:
            break
    return theta[:n]


def best_set(ids: list[str], score: dict[frozenset[str], float]) -> tuple[str, ...]:
    top = max(score.items(), key=lambda kv: kv[1])[0]
    return tuple(sorted(top))


def main() -> int:
    final = json.loads((RUN / "data" / "final.json").read_text())
    ids = list(final["ids"])
    ms = matches(RUN)
    q = panel_quality(PANEL)
    rng = np.random.default_rng(np.random.SeedSequence().entropy)  # fresh seed, recorded below

    # current rule: the run's own posterior-mode top 3
    current = tuple(sorted(sorted(ids, key=lambda x: final["rank"][x])[:3]))

    # portfolio rule (I003): maximise E[max beta] over posterior draws
    events = [
        PairEvent(m["first"], m["second"], m["preferred"] == "first", m["judge_id"]) for m in ms
    ]
    f = fit(ids, events, [], prior_scale=PRIOR)
    draws = rng.multivariate_normal(np.append(f.beta, f.gamma), f.covariance, size=DRAWS)[:, :-1]
    pos = {x: i for i, x in enumerate(f.ids)}
    emax = {
        frozenset(s): float(draws[:, [pos[x] for x in s]].max(axis=1).mean())
        for s in itertools.combinations(ids, 3)
    }
    portfolio = best_set(ids, emax)

    # reliability rule (I008): weights from the ETF brief
    agree = model_agreement()
    w = {k: max(0.0, 2 * a - 1) for k, a in agree.items()}
    seen = float(np.mean(list(w.values()))) if w else 1.0
    models = sorted({m["judge_model"] for m in ms})
    weights = {m: w.get(m, seen) for m in models}
    beta_w = weighted_fit(ids, ms, weights)
    reliability = tuple(sorted(str(x) for x in np.array(ids)[np.argsort(-beta_w)[:3]]))

    oracle = tuple(sorted(sorted(ids, key=lambda x: -q[x])[:3]))
    all_sets = list(itertools.combinations(ids, 3))

    def score(s: tuple[str, ...]) -> tuple[float, float]:
        vals = [q[x] for x in s]
        return max(vals), float(np.mean(vals))

    rows = {
        "current": current,
        "portfolio": portfolio,
        "reliability": reliability,
        "oracle": oracle,
    }
    out: dict[str, Any] = {
        "quality_pursue": q,
        "etf_model_agreement": agree,
        "weights": weights,
        "random_mean": {
            "best_of_3": float(np.mean([score(s)[0] for s in all_sets])),
            "mean_of_3": float(np.mean([score(s)[1] for s in all_sets])),
        },
        "rules": {
            k: {"set": list(v), "best_of_3": score(v)[0], "mean_of_3": score(v)[1]}
            for k, v in rows.items()
        },
    }
    (REPO / "benchmark/experiments/selection_rules.json").write_text(json.dumps(out, indent=2))
    print(
        "panel pursue per idea:",
        {k: round(v, 2) for k, v in sorted(q.items(), key=lambda kv: -kv[1])},
    )
    print(
        "ETF agreement per judge model:",
        {k: round(v, 2) for k, v in agree.items()},
        "-> weights",
        {k: round(v, 2) for k, v in weights.items()},
    )
    for k, v in out["rules"].items():
        print(f"{k:12s} {v['set']}  best-of-3 {v['best_of_3']:.2f}  mean-of-3 {v['mean_of_3']:.2f}")
    r = out["random_mean"]
    print(
        f"{'random':12s} (mean of 56 sets)      best-of-3 {r['best_of_3']:.2f}  mean-of-3 {r['mean_of_3']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
