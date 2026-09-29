"""Selection: gate bars, workshop slots, wildcards, and the family-aware shortlist.

Nothing here removes an idea from the report (DESIGN.md §4, "rank, don't
remove"); selection only decides which ideas get more work (workshop slots)
and which are highlighted (top families, wildcards).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from agent_brainswarm.critique import CheckedCritique
from agent_brainswarm.models import Ranking, Rating

SlotKind = Literal["value", "wildcard", "deepen", "advocate"]


@dataclass(frozen=True)
class Slot:
    """One workshop slot."""

    idea_id: str
    kind: SlotKind
    reason: str


@dataclass(frozen=True)
class Family:
    """A shortlisted idea and the variants from its cluster."""

    lead: str
    variants: tuple[str, ...]
    cluster: str


def gate_status(
    checked: Sequence[CheckedCritique], reviewers: Mapping[str, int]
) -> dict[str, Literal["barred", "fixable"]]:
    """Gate outcome per idea from counting critiques that cite a gate.

    An idea is *barred* when at least half of its reviewers raised a counting
    (unflagged), still-open or conceded *fatal* critique citing a gate; it is
    *fixable* when any counting critique cites a gate at lower severity.
    Barred ideas stay in the report with the reason; they are never
    shortlisted.
    """
    fatal: dict[str, set[str]] = defaultdict(set)
    fixable: set[str] = set()
    for item in checked:
        c = item.critique
        if not item.counts or c.gate is None or c.resolution in ("fixed", "rebutted"):
            continue
        if c.severity == "fatal":
            fatal[c.idea_id].add(c.critic_id)
        else:
            fixable.add(c.idea_id)
    out: dict[str, Literal["barred", "fixable"]] = {}
    for idea, critics in fatal.items():
        if 2 * len(critics) >= reviewers.get(idea, 1):
            out[idea] = "barred"
    for idea in fixable:
        out.setdefault(idea, "fixable")
    return out


def disagreement(
    rankings: Sequence[Ranking], batches: Mapping[str, Sequence[str]]
) -> dict[str, float]:
    """Bernoulli variance p(1-p) of "made this critic's top list".

    ``p`` is the fraction of critics who reviewed the idea and put it in
    their truncated ranking. The variance peaks at 0.25 when critics split
    evenly, which is what makes an idea divisive.
    """
    shown: dict[str, int] = defaultdict(int)
    picked: dict[str, int] = defaultdict(int)
    for r in rankings:
        if r.criterion != "overall":
            continue
        for x in batches.get(r.critic_id, ()):
            shown[x] += 1
        for x in r.order:
            picked[x] += 1
    return {x: (picked[x] / n) * (1 - picked[x] / n) for x, n in shown.items() if n}


def upside_gap(ratings: Sequence[Rating]) -> dict[str, float]:
    """Mean upside minus mean probability (1-5 scales): high = long shot with big payoff."""
    ups: dict[str, list[int]] = defaultdict(list)
    probs: dict[str, list[int]] = defaultdict(list)
    for r in ratings:
        ups[r.idea_id].append(r.upside)
        probs[r.idea_id].append(r.probability)
    return {x: mean(ups[x]) - mean(probs[x]) for x in ups}


def workshop_slots(
    value_order: Sequence[str],
    novelty_order: Sequence[str],
    disagreement_score: Mapping[str, float],
    gap_score: Mapping[str, float],
    split: tuple[int, int, int],
    deepen_candidates: Sequence[str],
    barred: set[str],
) -> list[Slot]:
    """Fill value, wildcard, and deepen slots; unused deepen slots go to value.

    Wildcards rotate through three lists (most novel, most divisive, biggest
    upside-over-probability gap) so no single notion of "unusual" dominates.
    """
    n_value, n_wild, n_deepen = split
    chosen: list[Slot] = []
    taken: set[str] = set(barred)

    deepen = [x for x in deepen_candidates if x not in taken][:n_deepen]
    for x in deepen:
        chosen.append(Slot(x, "deepen", "library idea worth pushing further"))
        taken.add(x)
    n_value += n_deepen - len(deepen)

    for x in value_order:
        if sum(s.kind == "value" for s in chosen) >= n_value:
            break
        if x not in taken:
            chosen.append(Slot(x, "value", "high preliminary value"))
            taken.add(x)

    by_disagreement = sorted(disagreement_score, key=lambda x: -disagreement_score[x])
    by_gap = sorted(gap_score, key=lambda x: -gap_score[x])
    lists = [
        (list(novelty_order), "most novel"),
        (by_disagreement, "most divisive among critics"),
        (by_gap, "high upside, low probability"),
    ]
    cursor = [0, 0, 0]
    wild = 0
    while wild < n_wild and any(cursor[i] < len(lists[i][0]) for i in range(3)):
        for i, (items, reason) in enumerate(lists):
            if wild >= n_wild:
                break
            while cursor[i] < len(items) and items[cursor[i]] in taken:
                cursor[i] += 1
            if cursor[i] < len(items):
                x = items[cursor[i]]
                chosen.append(Slot(x, "wildcard", reason))
                taken.add(x)
                wild += 1
    return chosen


def top_families(
    order: Sequence[str],
    cluster_of: Mapping[str, str],
    tier: Mapping[str, int],
    k: int,
    barred: set[str],
) -> list[Family]:
    """Best idea per distinct cluster, in rank order, until ``k`` families.

    Ties at the cutoff are kept: after the k-th family, further families
    whose lead shares the k-th lead's tier are added.
    """
    families: list[Family] = []
    seen: set[str] = set()
    for x in order:
        if x in barred:
            continue
        cluster = cluster_of.get(x, x)
        if cluster in seen:
            continue
        if len(families) >= k and tier.get(x) != tier.get(families[k - 1].lead):
            break
        seen.add(cluster)
        variants = tuple(y for y in order if y != x and cluster_of.get(y, y) == cluster)
        families.append(Family(x, variants, cluster))
    return families
