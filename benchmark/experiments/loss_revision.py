"""Stage 2 experiment: loss-conditioned revision with a two-order gate (idea I004 of the self-run).

    uv run python benchmark/experiments/loss_revision.py revise    # write revision tasks
    uv run python benchmark/experiments/loss_revision.py gate      # after revisions: gate tasks
    uv run python benchmark/experiments/loss_revision.py panel     # after revisions: panel tasks
    uv run python benchmark/experiments/loss_revision.py analyze   # after gate and panel

Design (on the 8 finalists of examples/runs/2026-09-29-beat-baseline):

1. Revision. For each idea, a developer of a model family other than the author's writes one
   revision per arm: ``treatment`` receives the judges' stated reasons for each finals loss;
   ``control`` receives only "make it stronger". Both must stay within 5 % of the original's
   word count (checked by code), so any gain is not bought with length.
2. Gate (the mechanism under test). A judge of a family other than the developer's compares
   original and revision in both orders, in separate dispatches; the revision is accepted only
   if it wins both orders.
3. Evaluation. A panel of three reviewers (one per family) compares every revision with its
   original in both orders, in separate dispatches, whatever the gate decided.

Outcomes: the panel's preference for revisions over originals per arm (the effect of loss
reasons), and the panel's preference among gate-accepted versus gate-rejected revisions (whether
the gate selects real improvements).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark"))
from make_pack import render

RUN = REPO / "examples/runs/2026-09-29-beat-baseline"
OUT = REPO / "benchmark/experiments/loss-revision"
FAMILIES = ("opus", "sonnet", "fable")
LENGTH_SLACK = 1.05  # "same-length revision": at most 5 % more words than the original
CARD_KEYS = (
    "title",
    "pitch",
    "mechanism",
    "rationale",
    "assumptions",
    "failure_modes",
    "cheapest_test",
    "effort",
    "spec",
)


def words(card: dict[str, Any]) -> int:
    return len(render("?", card).split())


def cards() -> dict[str, dict[str, Any]]:
    data = json.loads((RUN / "data" / "cards.json").read_text())
    final = json.loads((RUN / "data" / "final.json").read_text())
    return {x: data[x] for x in final["ids"]}


def losses(idea: str) -> list[str]:
    out = []
    for m in json.loads((RUN / "data" / "matches.json").read_text()):
        winner = m["first"] if m["preferred"] == "first" else m["second"]
        if idea in (m["first"], m["second"]) and winner != idea and m.get("reason"):
            out.append(m["reason"])
    return out


def other(family: str, *avoid: str) -> str:
    return next(f for f in FAMILIES if f not in (family, *avoid))


def card_json(card: dict[str, Any]) -> str:
    return json.dumps({k: card.get(k) for k in CARD_KEYS}, indent=1)


def revise() -> int:
    (OUT / "tasks").mkdir(parents=True, exist_ok=True)
    (OUT / "out").mkdir(parents=True, exist_ok=True)
    plan: dict[str, Any] = {}
    groups: dict[tuple[str, str], list[str]] = {}
    for idea, c in cards().items():
        dev = other(c["provenance"]["model"])
        plan[idea] = {
            "author": c["provenance"]["model"],
            "developer": dev,
            "words": words(c),
            "losses": len(losses(idea)),
        }
        for arm in ("treatment", "control"):
            groups.setdefault((arm, dev), []).append(idea)
    for (arm, dev), ideas in groups.items():
        blocks = []
        for idea in ideas:
            c = cards()[idea]
            cap = int(words(c) * LENGTH_SLACK)
            why = "\n".join(f"- {r}" for r in losses(idea)) or "- (it lost no comparisons)"
            guidance = (
                f"Judges' reasons for each comparison this idea lost in the finals:\n{why}\n\n"
                "Revise the card to address these reasons."
                if arm == "treatment"
                else "Revise the card to make it stronger."
            )
            blocks.append(
                f"## Idea {idea}\n\n```json\n{card_json(c)}\n```\n\n{guidance} It must stay the same "
                f"idea. The revised card may have at most {cap} words in total (the original has "
                f"{words(c)})."
            )
        did = f"{arm}-{dev}"
        target = (OUT / "out" / f"{did}.json").resolve()
        text = (
            "# Idea revision task\n\nYou revise idea cards for a system that generates ideas for "
            "the brief below. Read no file other than this one.\n\n## Brief\n\n"
            + (RUN / "brief.md").read_text().strip()
            + "\n\n"
            + "\n\n".join(blocks)
            + f"\n\n## Output\n\nWrite one JSON object to `{target}`: "
            '{"revisions": {"<idea id>": {<the card fields: title, pitch, mechanism, rationale, '
            "assumptions (list), failure_modes (list), cheapest_test, effort, spec>}}}, with one "
            "entry for every idea above.\n"
        )
        (OUT / "tasks" / f"{did}.md").write_text(text)
        plan.setdefault("_dispatches", []).append({"id": did, "model": dev, "ideas": ideas})
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2))
    for d in plan["_dispatches"]:
        print(d["id"], d["model"], len(d["ideas"]), "ideas")
    return 0


def revisions() -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for path in sorted((OUT / "out").glob("*.json")):
        arm = path.stem.split("-")[0]
        if arm not in ("treatment", "control"):
            continue
        for idea, card in json.loads(path.read_text())["revisions"].items():
            out[(arm, idea)] = card
    return out


def comparison_tasks(kind: str, judges: dict[tuple[str, str], list[str]]) -> int:
    """Pairwise tasks: for each (arm, idea) and judge family, both orders in separate dispatches."""
    originals, revs = cards(), revisions()
    (OUT / "tasks").mkdir(parents=True, exist_ok=True)
    batches: dict[tuple[str, int], list[tuple[str, str, str]]] = {}
    for (arm, idea), fams in judges.items():
        for fam in fams:
            for order in (0, 1):
                batches.setdefault((fam, order), []).append((arm, idea, fam))
    key: dict[str, Any] = {}
    for (fam, order), items in batches.items():
        did = f"{kind}-{fam}-{order}"
        target = (OUT / "out" / f"{did}.json").resolve()
        blocks = []
        for n, (arm, idea, _) in enumerate(items, start=1):
            a, b = originals[idea], revs[(arm, idea)]
            first, second = (a, b) if order == 0 else (b, a)
            pid = f"p{n:02d}"
            key[f"{did}/{pid}"] = {"arm": arm, "idea": idea, "revised_first": order == 1}
            blocks.append(f"## Pair {pid}\n\n{render('X', first)}\n\n{render('Y', second)}")
        text = (
            "# Pairwise judgement task\n\nFor each pair, decide which version of the idea you would "
            "rather pursue for the brief below. Judge substance, not length or polish; the order "
            "carries no information. Read no file other than this one.\n\n## Brief\n\n"
            + (RUN / "brief.md").read_text().strip()
            + "\n\n"
            + "\n\n".join(blocks)
            + f"\n\n## Output\n\nWrite one JSON object to `{target}`: "
            '{"verdicts": [{"pair": "p01", "winner": "X or Y", "reason": "one sentence"}]}, '
            "one verdict per pair.\n"
        )
        (OUT / "tasks" / f"{did}.md").write_text(text)
        print(did, fam, len(items), "pairs")
    (OUT / f"{kind}-key.json").write_text(json.dumps(key, indent=2))
    return 0


def gate() -> int:
    plan = json.loads((OUT / "plan.json").read_text())
    judges = {
        (arm, idea): [other(plan[idea]["developer"], plan[idea]["author"])]
        for arm, idea in revisions()
    }
    return comparison_tasks("gate", judges)


def panel() -> int:
    return comparison_tasks("panel", {k: list(FAMILIES) for k in revisions()})


def verdicts(kind: str) -> dict[tuple[str, str], list[bool]]:
    """(arm, idea) -> list of 'revision won' per ordered comparison."""
    key = json.loads((OUT / f"{kind}-key.json").read_text())
    out: dict[tuple[str, str], list[bool]] = {}
    for path in sorted((OUT / "out").glob(f"{kind}-*.json")):
        for v in json.loads(path.read_text())["verdicts"]:
            k = key[f"{path.stem}/{v['pair']}"]
            revised_won = (v["winner"].strip().upper() == "Y") != k["revised_first"]
            out.setdefault((k["arm"], k["idea"]), []).append(revised_won)
    return out


def analyze() -> int:
    plan = json.loads((OUT / "plan.json").read_text())
    revs = revisions()
    g, p = verdicts("gate"), verdicts("panel")
    rows = []
    for (arm, idea), card in sorted(revs.items()):
        cap = int(plan[idea]["words"] * LENGTH_SLACK)
        rows.append(
            {
                "arm": arm,
                "idea": idea,
                "words": words(card),
                "cap": cap,
                "within_cap": words(card) <= cap,
                "accepted": all(g.get((arm, idea), [False])) and len(g.get((arm, idea), [])) == 2,
                "panel_win_rate": float(np.mean(p[(arm, idea)])) if (arm, idea) in p else None,
                "panel_n": len(p.get((arm, idea), [])),
            }
        )
    summary: dict[str, Any] = {}
    for arm in ("treatment", "control"):
        mine = [r for r in rows if r["arm"] == arm]
        acc = [r for r in mine if r["accepted"]]
        rej = [r for r in mine if not r["accepted"]]
        summary[arm] = {
            "revisions": len(mine),
            "within_cap": sum(1 for r in mine if r["within_cap"]),
            "accepted": len(acc),
            "panel_win_rate_all": float(np.mean([r["panel_win_rate"] for r in mine])),
            "panel_win_rate_accepted": float(np.mean([r["panel_win_rate"] for r in acc]))
            if acc
            else None,
            "panel_win_rate_rejected": float(np.mean([r["panel_win_rate"] for r in rej]))
            if rej
            else None,
        }
    (OUT / "results.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2))
    for r in rows:
        print(
            f"{r['arm']:9s} {r['idea']}  words {r['words']:3d}/{r['cap']:3d}  gate {'accept' if r['accepted'] else 'reject'}  panel win {r['panel_win_rate']:.2f} (n={r['panel_n']})"
        )
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["revise", "gate", "panel", "analyze"])
    step = parser.parse_args().step
    return {"revise": revise, "gate": gate, "panel": panel, "analyze": analyze}[step]()


if __name__ == "__main__":
    raise SystemExit(main())
