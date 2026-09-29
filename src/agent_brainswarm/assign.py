"""Phase 1 -> 2: popularity banding and stratified slot assignment (DESIGN.md §6).

Inputs are the blind angle/domain pools and the LLM clusterer's grouping of
them (code validates the grouping and counts; the model only groups).
Popularity of a cluster, ``s_k``, is the number of *distinct* generators
that proposed something in it. Bands use fixed thresholds: rare ``s_k = 1``,
middle ``2 <= s_k <= 3``, common ``s_k >= 4``. Tertiles were rejected
because most of ~60 free-text angles form singleton clusters, which makes
both tertile cut points equal 1 and empties the rare band. Slots are split
across bands by largest-remainder rounding; an empty band's share moves to
the adjacent band and the move is logged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from agent_brainswarm.config import RunConfig, largest_remainder
from agent_brainswarm.models import Angle, Band, SlotType

BANDS: tuple[Band, Band, Band] = ("common", "middle", "rare")
SLOT_TYPES: tuple[SlotType, SlotType, SlotType] = ("angle", "free", "cross_domain")
DISTANCE_TO_BAND: dict[str, Band] = {"near": "common", "mid": "middle", "far": "rare"}


@dataclass(frozen=True)
class Assignment:
    """What one generator is asked to do in Phase 2."""

    generator_id: str
    model: str
    slot_type: SlotType
    angle_id: str | None
    band: Band | None


# Popularity thresholds (distinct proposers): 4+ of ~20 generators is a
# clear convergence; a single proposer is by definition idiosyncratic.
COMMON_MIN = 4
MIDDLE_MIN = 2


def popularity(clusters: Mapping[str, Sequence[Angle]]) -> dict[str, int]:
    """Number of distinct proposers per cluster."""
    return {cid: len({a.proposer for a in angles}) for cid, angles in clusters.items()}


def band_clusters(clusters: Mapping[str, Sequence[Angle]]) -> dict[str, Band]:
    """Band angle clusters by popularity with the fixed thresholds above."""
    return {
        cid: "common" if s >= COMMON_MIN else "middle" if s >= MIDDLE_MIN else "rare"
        for cid, s in popularity(clusters).items()
    }


def band_domains(clusters: Mapping[str, Sequence[Angle]]) -> dict[str, Band]:
    """Band domain clusters by the proposers' majority distance rating."""
    out: dict[str, Band] = {}
    for cid, domains in clusters.items():
        ratings = [d.distance for d in domains if d.distance]
        majority = max(set(ratings), key=ratings.count) if ratings else "mid"
        out[cid] = DISTANCE_TO_BAND[majority]
    return out


def _allocate(
    receivers: Sequence[str],
    clusters: Mapping[str, Sequence[Angle]],
    bands: Mapping[str, Band],
    shares: tuple[float, float, float],
    rng: np.random.Generator,
) -> dict[str, tuple[Angle, Band]]:
    """Give each receiver one angle, stratified by band."""
    present = [b for b in BANDS if any(v == b for v in bands.values())]
    if not receivers or not present:
        return {}
    counts = dict(zip(BANDS, largest_remainder(len(receivers), shares), strict=True))
    # An empty band cannot receive slots: move them to the nearest present
    # band (middle first, since it is adjacent to both ends).
    for band in BANDS:
        if band not in present and counts[band]:
            nearest = min(
                present, key=lambda b: (abs(BANDS.index(b) - BANDS.index(band)), b != "middle")
            )
            counts[nearest] += counts[band]
            counts[band] = 0
    order = list(receivers)
    rng.shuffle(order)
    out: dict[str, tuple[Angle, Band]] = {}
    cursor = 0
    for band in BANDS:
        band_clusters_ids = sorted(cid for cid, b in bands.items() if b == band)
        draws: list[str] = []
        while len(draws) < counts[band]:
            # Uniform over clusters without replacement; reshuffle when exhausted.
            draws += list(rng.permutation(band_clusters_ids))
        for cid in draws[: counts[band]]:
            receiver = order[cursor]
            cursor += 1
            options = [a for a in clusters[cid] if a.proposer != receiver] or list(clusters[cid])
            out[receiver] = (options[int(rng.integers(len(options)))], band)
    return out


def assign_slots(
    config: RunConfig,
    generator_ids: Sequence[str],
    angle_clusters: Mapping[str, Sequence[Angle]],
    domain_clusters: Mapping[str, Sequence[Angle]],
) -> list[Assignment]:
    """Decide every generator's slot type and, where relevant, its angle or domain."""
    rng = np.random.default_rng(config.seed)
    ids = list(generator_ids)
    counts = largest_remainder(len(ids), config.slot_mix)
    order = list(ids)
    rng.shuffle(order)
    by_type: dict[SlotType, list[str]] = {}
    start = 0
    for slot, n in zip(SLOT_TYPES, counts, strict=True):
        by_type[slot] = order[start : start + n]
        start += n
    models = config.generator_models
    model_of = {g: models[i % len(models)] for i, g in enumerate(ids)}
    angles = _allocate(
        by_type["angle"], angle_clusters, band_clusters(angle_clusters), config.angle_bands, rng
    )
    domains = _allocate(
        by_type["cross_domain"],
        domain_clusters,
        band_domains(domain_clusters),
        config.distance_bands,
        rng,
    )
    result: list[Assignment] = []
    for g in ids:
        if g in angles:
            angle, band = angles[g]
            result.append(Assignment(g, model_of[g], "angle", angle.id, band))
        elif g in domains:
            domain, band = domains[g]
            result.append(Assignment(g, model_of[g], "cross_domain", domain.id, band))
        else:
            # Free slots, and angle/domain slots whose pool was empty, degrade to free.
            result.append(Assignment(g, model_of[g], "free", None, None))
    return result
