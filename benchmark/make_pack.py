"""Build a blinded human-judging pack: brainswarm's top k finalists vs a single agent's top k.

    uv run python benchmark/make_pack.py <brainswarm-run> <baseline.json> <out-dir> [--k 3]

Both sides are rendered in one card format with the same fields; sources, ids, and provenance
are dropped so the reader cannot tell which system wrote a card except by its content. The
order is shuffled with a seed drawn from OS entropy by numpy and recorded in ``key.json``,
which the judge must not open until the ratings are written. See docs/BENCHMARK.md.
"""

from __future__ import annotations

import argparse
import json
import string
from pathlib import Path
from typing import Any

import numpy as np

FIELDS = (
    ("pitch", "Pitch"),
    ("mechanism", "Mechanism"),
    ("rationale", "Rationale"),
    ("assumptions", "Assumptions"),
    ("failure_modes", "How it fails"),
    ("cheapest_test", "Cheapest test"),
    ("effort", "Effort"),
    ("spec", "Operational spec"),
)


def render(label: str, card: dict[str, Any]) -> str:
    """One card as markdown, in the shared format."""
    lines = [f"## Idea {label}: {card['title']}", ""]
    for key, name in FIELDS:
        value = card.get(key)
        if not value:
            continue
        text = "; ".join(value) if isinstance(value, list) else str(value)
        lines += [f"**{name}.** {text}", ""]
    return "\n".join(lines)


def brainswarm_top(run: Path, k: int) -> list[dict[str, Any]]:
    """The top k finalists of a finished brainswarm run, by final rank."""
    final = json.loads((run / "data" / "final.json").read_text())
    cards = json.loads((run / "data" / "cards.json").read_text())
    ranked = sorted(final["ids"], key=lambda x: final["rank"][x])[:k]
    return [{**cards[x], "origin": f"brainswarm {x}"} for x in ranked]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text())["top3"][: args.k]
    entries = brainswarm_top(args.run, args.k) + [
        {**c, "origin": f"single agent #{i + 1}"} for i, c in enumerate(baseline)
    ]
    entropy = np.random.SeedSequence().entropy  # fresh OS entropy, recorded in key.json
    assert isinstance(entropy, int)  # a SeedSequence built without arguments draws one int
    seed = entropy
    order = np.random.default_rng(seed).permutation(len(entries))
    labels = string.ascii_uppercase[: len(entries)]

    brief = (args.run / "brief.md").read_text().strip()
    rows = "\n".join(f"| {x} | | | | | | |" for x in labels)
    pack = [
        "# Blinded idea comparison",
        "",
        (
            "Six ideas for the brief below, in random order. Some were written by a multi-agent "
            "system and some by a single agent; do not try to guess which. Rate each idea on its "
            "own merits, then rank all six. Do not open `key.json` until the table is filled in."
        ),
        "",
        "## Brief",
        "",
        brief,
        "",
        "## Ratings",
        "",
        (
            "Score 1 (poor) to 5 (excellent). *Constraints*: how convincingly the idea meets the "
            "brief's hard rules (trading days, turnover, daily closes, long only). *Drawdown*: "
            "how credible the case for staying under 20 % is. *Growth*, *Diversification*: as "
            "named. *Would pursue*: would you spend a week testing this? Rank: 1 = best of the six."
        ),
        "",
        "| Idea | Constraints | Drawdown | Growth | Diversification | Would pursue | Rank |",
        "|---|---|---|---|---|---|---|",
        rows,
        "",
        *[render(labels[j], entries[i]) for j, i in enumerate(order)],
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pack.md").write_text("\n".join(pack))
    key = {labels[j]: entries[i]["origin"] for j, i in enumerate(order)}
    (args.out / "key.json").write_text(json.dumps({"seed": seed, "labels": key}, indent=2))
    print(f"wrote {args.out / 'pack.md'} and key.json (seed {seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
