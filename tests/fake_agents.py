"""Deterministic stand-ins for every agent role (fixture mode).

Each fake reads the run's code-owned state (as a real agent would read its
task file) and writes schema-valid JSON. Ideas carry a hidden latent
quality so tests can check that the pipeline's ranking recovers it.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import numpy as np

from agent_brainswarm.state import Run

ANGLE_POOL = [
    "momentum across assets",
    "mean reversion after shocks",
    "volatility targeting",
    "sector rotation by breadth",
    "carry and term structure",
    "seasonality effects",
]


def _rng(key: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:8], 16))


def quality(title: str) -> float:
    """Hidden latent quality of an idea, recoverable from its title."""
    return float(_rng("quality:" + title).normal())


def rubric_draft(brief: str) -> dict[str, Any]:
    return {
        "brief": brief,
        "criteria": [
            {
                "name": "legal_and_ethical",
                "kind": "gate",
                "definition": "Legal and ethical.",
                "user_stated": False,
            },
            {
                "name": "trades_daily",
                "kind": "gate",
                "definition": "Trades on most days.",
                "user_stated": True,
            },
            {
                "name": "growth",
                "kind": "judged",
                "definition": "Long-run growth.",
                "anchors": ["high: compounding edge"],
            },
            {"name": "diversification", "kind": "judged", "definition": "Spread of risk."},
        ],
        "assumptions": ["Long-only ETFs"],
    }


def respond(run: Run, phase: str, dispatch_id: str) -> dict[str, Any]:
    """The fake agent output for one dispatch."""
    rng = _rng(f"{phase}:{dispatch_id}")
    cfg = run.read("config.json")
    if phase == "audit":
        return {"issues": [{"criterion": None, "problem": "none", "suggestion": "none"}]}
    if phase == "angles":
        picks = rng.choice(len(ANGLE_POOL), size=cfg["angles_per_generator"], replace=False)
        return {
            "angles": [ANGLE_POOL[int(i)] for i in picks],
            "domains": [
                {
                    "text": f"domain {int(rng.integers(5))}",
                    "distance": ["near", "mid", "far"][int(rng.integers(3))],
                }
                for _ in range(cfg["domains_per_generator"])
            ],
        }
    if phase == "angle_clusters":
        pools = run.read("data", "angles.json")
        out: dict[str, list[list[str]]] = {}
        for key, name in (("angles", "angle_clusters"), ("domains", "domain_clusters")):
            groups: dict[str, list[str]] = {}
            for a in pools[key]:
                groups.setdefault(a["text"], []).append(a["id"])
            out[name] = list(groups.values())
        return out
    if phase == "ideate":
        return {
            "ideas": [
                {"title": f"{dispatch_id} idea {k}", "sketch": "A sketch."}
                for k in range(cfg["ideas_per_generator"])
            ]
        }
    if phase == "research":
        return {
            "cards": [
                {
                    "title": f"{dispatch_id} idea {k}",
                    "pitch": f"Pitch for {dispatch_id} idea {k}.",
                    "mechanism": f"Rebalance weekly toward assets with rising {k}-month momentum and cap each weight.",
                    "rationale": "Momentum persists over months in many asset classes.",
                    "assumptions": ["Liquid ETFs", "Low costs"],
                    "failure_modes": ["Momentum crashes"],
                    "cheapest_test": "Backtest 2005-2020, hold out 2021-2024.",
                    "effort": "Two days",
                    "sources": ["https://example.org/momentum"],
                    "spec": None,
                    "raw_index": k if k < cfg["ideas_per_generator"] - 1 else None,
                    "transfer": None,
                }
                for k in range(cfg["ideas_per_generator"])
            ]
        }
    if phase == "idea_clusters":
        cards = run.read("data", "cards.json")
        ids = sorted(cards)
        return {
            "clusters": [{"id": f"C{i}", "members": ids[i : i + 2]} for i in range(0, len(ids), 2)],
            "library": {x: {"relation": "new", "library_id": None} for x in ids},
        }
    if phase in ("critique", "recritique"):
        name = "critic_batches.json" if phase == "critique" else "recritic_batches.json"
        batch = next(b["ideas"] for b in run.read("data", name) if b["dispatch_id"] == dispatch_id)
        cards = run.read("data", "cards.json")
        crits = []
        for x in batch:
            words = cards[x]["mechanism"].split()[:6]
            crits.append(
                {
                    "idea_id": x,
                    "target": " ".join(words),
                    "mechanism": f"Weekly rebalancing for {x} incurs turnover that erodes the edge after costs.",
                    "evidence": "Typical ETF spreads of 2-5 bp times weekly turnover.",
                    "severity": ["fatal", "major", "minor"][int(rng.integers(3))],
                    "falsifier": "A cost-inclusive backtest with positive net return.",
                    "gate": None,
                }
            )
        out: dict[str, Any] = {"critiques": crits}
        if phase == "critique":
            noisy = sorted(batch, key=lambda x: -(quality(cards[x]["title"]) + 0.3 * rng.normal()))
            depth = min(3, len(batch))
            out |= {
                "ranking": noisy[:depth],
                "novelty_ranking": [str(x) for x in rng.permutation(batch)[:depth]],
                "ratings": [
                    {
                        "idea_id": x,
                        "upside": int(rng.integers(1, 6)),
                        "probability": int(rng.integers(1, 6)),
                    }
                    for x in batch
                ],
            }
        else:
            responses = run.read("data", "responses.json")
            out |= {
                "response_verdicts": [
                    {"critique_id": cid, "holds": bool(rng.integers(2))}
                    for cid, r in responses.items()
                    if r["idea"] in batch
                ],
                "same_idea": [{"idea_id": x, "same": True} for x in batch],
            }
        return out
    if phase == "checker":
        task = run.path("tasks", "checker", f"{dispatch_id}.md").read_text()
        ids = re.findall(r"^### (\S+)$", task, flags=re.MULTILINE)
        return {
            "verdicts": [{"critique_id": c, "transfers": bool(rng.random() < 0.1)} for c in ids]
        }
    if phase == "advocate":
        return {"promote": []}
    if phase == "workshop":
        idea = dispatch_id.split("-")[1]
        cards = run.read("data", "cards.json")
        latest = max(
            (k for k in cards if k == idea or k.startswith(idea + "-")),
            key=lambda k: cards[k]["version"],
        )
        crits = [
            c
            for name in ("critiques.json", "recritiques.json")
            if run.exists("data", name)
            for c in run.read("data", name)
            if c["critique"]["idea_id"] == latest
        ]
        base = dict(cards[latest])
        draft = {
            k: base[k]
            for k in (
                "title",
                "pitch",
                "mechanism",
                "rationale",
                "assumptions",
                "failure_modes",
                "cheapest_test",
                "effort",
                "sources",
                "spec",
            )
        }
        draft["mechanism"] = base["mechanism"] + " Trade only when the signal changes rank."
        return {
            "card": draft,
            "responses": [
                {
                    "critique_id": c["critique"]["id"],
                    "resolution": ["fixed", "rebutted", "conceded"][i % 3],
                    "response": "Addressed.",
                }
                for i, c in enumerate(crits)
            ],
            "grafts": [],
        }
    if phase in ("finals", "boundary"):
        batch = next(
            b for b in run.read("data", "judge_batches.json") if b["dispatch_id"] == dispatch_id
        )
        cards = run.read("data", "cards.json")
        verdicts = []
        for i, (a, b) in enumerate(batch["pairs"]):
            margin = (
                quality(cards[a]["title"]) - quality(cards[b]["title"]) + 0.4 + 0.5 * rng.normal()
            )
            verdicts.append(
                {
                    "pair_id": f"{dispatch_id}-{i + 1:02d}",
                    "preferred": "first" if margin > 0 else "second",
                    "reason": "r",
                }
            )
        return {"verdicts": verdicts}
    if phase == "factcheck":
        return {"claims": [{"claim": "Momentum persists.", "status": "supported", "source": "x"}]}
    raise ValueError(phase)


def write_outputs(run: Run, step: dict[str, Any]) -> None:
    """Write every dispatch's output for a `next_step` result."""
    for d in step["dispatches"]:
        path = run.path("out", step["phase"], f"{d['id']}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(respond(run, step["phase"], d["id"])))
