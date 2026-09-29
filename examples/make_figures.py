"""README figures from the recorded demo run (zero tokens).

    uv run python examples/make_figures.py

Writes ``docs/figures/demo_pipeline.png`` (what each stage produced, counted from the run's
data) and ``docs/figures/demo_ranking.png`` (the finalists' ranks with 95 % intervals).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
RUN = HERE / "demo-run"
OUT = HERE.parent / "docs" / "figures"
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#e4e3dc", "#fcfcfb"
BLUE = "#2a78d6"  # reference categorical slot 1


def data(name: str) -> Any:
    return json.loads((RUN / "data" / name).read_text())


def stages() -> list[tuple[str, str, str]]:
    """(count, label, note) per stage, counted from the recorded run."""
    rubric = json.loads((RUN / "rubric.json").read_text())
    gates = sum(c["kind"] == "gate" for c in rubric["criteria"])
    judged = len(rubric["criteria"]) - gates
    angles = data("angles.json")
    cards = data("cards.json")
    first = [c for c in cards.values() if c.get("version", 1) == 1]
    cross = sum(c["provenance"]["slot_type"] == "cross_domain" for c in first)
    critiques = data("critiques.json")
    items = critiques if isinstance(critiques, list) else list(critiques.values())
    generic = sum("generic" in c.get("flags", []) for c in items)
    developed = [c for c in cards.values() if c.get("version", 1) == 2]
    recrit = data("recritiques.json")
    recrit_n = len(recrit if isinstance(recrit, list) else list(recrit.values()))
    matches = data("matches.json")
    return [
        (f"{gates} + {judged}", "rubric", "hard rules +\njudged criteria"),
        (
            f"{len(angles['angles'])} + {len(angles['domains'])}",
            "approaches",
            "angles + far\ndomains, blind",
        ),
        (str(len(first)), "ideas", f"sketched before any\nresearch; {cross} cross-domain"),
        (str(len(items)), "critiques", f"each quoting the idea;\n{generic} flagged generic"),
        (
            str(len(developed)),
            "developed",
            f"every serious critique\nanswered; {recrit_n} re-checks",
        ),
        (str(len(matches)), "verdicts", "pairwise finals,\nboth orders"),
        (str(len(first)), "ranked", "every idea kept,\nwith uncertainty"),
    ]


def pipeline(path: Path) -> None:
    rows = stages()
    fig, ax = plt.subplots(figsize=(12, 2.5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, len(rows))
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, (count, label, note) in enumerate(rows):
        box = FancyBboxPatch(
            (i + 0.06, 0.12),
            0.88,
            0.8,
            boxstyle="round,pad=0,rounding_size=0.06",
            facecolor="white",
            edgecolor=GRID,
            linewidth=1.2,
        )
        ax.add_patch(box)
        ax.text(
            i + 0.5, 0.72, count, ha="center", va="center", fontsize=17, color=BLUE, weight="bold"
        )
        ax.text(i + 0.5, 0.52, label, ha="center", va="center", fontsize=10.5, color=INK)
        ax.text(
            i + 0.5,
            0.28,
            note,
            ha="center",
            va="center",
            fontsize=7.5,
            color=MUTED,
            linespacing=1.3,
        )
        if i < len(rows) - 1:
            ax.annotate(
                "",
                xy=(i + 1.06, 0.52),
                xytext=(i + 0.94, 0.52),
                arrowprops={"arrowstyle": "-|>", "color": MUTED, "lw": 1.2},
            )
    fig.tight_layout(pad=0.3)
    fig.savefig(path, dpi=160, facecolor=SURFACE)


def ranking(path: Path) -> None:
    final = data("final.json")
    cards = data("cards.json")
    ids = sorted(final["ids"], key=lambda x: -final["rank"][x])
    fig, ax = plt.subplots(figsize=(9, 2.8), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for y, x in enumerate(ids):
        lo, hi = final["rank_interval"][x]
        ax.plot([lo, hi], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot(
            final["rank"][x],
            y,
            "o",
            color=BLUE,
            markersize=9,
            markeredgecolor=SURFACE,
            markeredgewidth=2,
        )
        ax.text(
            len(ids) + 0.35,
            y,
            f"beats others {final['mean_win'][x]:.0%}",
            va="center",
            fontsize=8.5,
            color=MUTED,
        )
    title = {x: cards[x]["title"].split(":")[0].split(" with ")[0] for x in ids}
    ax.set_yticks(
        range(len(ids)),
        [f"{title[x]} [{x.removesuffix('-v2')}]" for x in ids],
        color=INK,
        fontsize=9,
    )
    ax.set_xticks(range(1, len(ids) + 1))
    ax.set_xlim(0.6, len(ids) + 1.6)
    ax.set_xlabel("rank (1 = best); line = 95 % interval", color=INK, fontsize=9)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", colors=GRID, labelcolor=INK, labelsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=SURFACE)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline(OUT / "demo_pipeline.png")
    ranking(OUT / "demo_ranking.png")
    for row in stages():
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
