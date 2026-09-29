"""Scoring: closed forms, recovery of known parameters, and uncertainty methods."""

import itertools

import choix
import numpy as np
import pytest

from agent_brainswarm.scoring import (
    MIN_CLUSTERS,
    PairEvent,
    RankingEvent,
    components,
    fit,
    mean_win_probability,
    score,
)

# A prior scale this wide makes the penalty negligible, so fits approach the
# unpenalised maximum-likelihood estimate that closed forms describe.
FLAT = 100.0


def _pairs(a: str, b: str, wins_a: int, wins_b: int) -> list[PairEvent]:
    """Balanced presentation: each result appears once in each order, so gamma -> 0."""
    events = []
    for i in range(wins_a):
        events.append(
            PairEvent(a, b, True, f"d{i}") if i % 2 == 0 else PairEvent(b, a, False, f"d{i}")
        )
    for i in range(wins_b):
        events.append(
            PairEvent(b, a, True, f"e{i}") if i % 2 == 0 else PairEvent(a, b, False, f"e{i}")
        )
    return events


def test_two_idea_closed_form() -> None:
    # A beats B 4-2 with balanced orders: beta_A - beta_B = log(4/2) = ln 2.
    f = fit(["A", "B"], _pairs("A", "B", 4, 2), prior_scale=FLAT)
    assert f.beta[0] - f.beta[1] == pytest.approx(np.log(2), abs=1e-3)
    assert abs(f.gamma) < 1e-3


def test_sum_to_zero_is_automatic() -> None:
    f = fit(["A", "B", "C"], _pairs("A", "B", 3, 1) + _pairs("B", "C", 2, 2), prior_scale=1.5)
    assert f.beta.sum() == pytest.approx(0.0, abs=1e-9)


def test_unique_maximum_from_any_start() -> None:
    events = _pairs("A", "B", 5, 1) + _pairs("B", "C", 2, 3) + _pairs("A", "C", 4, 4)
    a = fit(["A", "B", "C"], events)
    b = fit(["A", "B", "C"], events, start=np.array([3.0, -2.0, 1.0, 0.7]))
    assert np.allclose(a.beta, b.beta, atol=1e-7)


def test_undefeated_idea_has_finite_strength() -> None:
    f = fit(["A", "B"], _pairs("A", "B", 6, 0))
    assert np.isfinite(f.beta).all()


def test_position_bias_is_recovered() -> None:
    # Simulate from known strengths and gamma = 0.8; 5 ideas, 400 ordered matches.
    rng = np.random.default_rng(7)
    beta = np.array([1.0, 0.5, 0.0, -0.5, -1.0])
    ids = list("ABCDE")
    events = []
    for m in range(400):
        i, j = rng.choice(5, size=2, replace=False)
        p_first = 1 / (1 + np.exp(-(beta[i] - beta[j] + 0.8)))
        events.append(PairEvent(ids[i], ids[j], bool(rng.random() < p_first), f"c{m % 40}"))
    f = fit(ids, events, prior_scale=FLAT)
    assert f.gamma == pytest.approx(0.8, abs=0.3)
    assert list(np.argsort(-f.beta)) == [0, 1, 2, 3, 4]


def test_plackett_luce_two_item_ranking_equals_pair() -> None:
    # A 2-item ranking is the same likelihood as one pairwise win (with gamma pinned).
    r = fit(["A", "B"], rankings=[RankingEvent(("A",), ("A", "B"), "c")], prior_scale=1.5)
    p = fit(
        ["A", "B"],
        [PairEvent("A", "B", True, "c"), PairEvent("B", "A", False, "c")],
        prior_scale=1.5,
    )
    # Two balanced pair events carry twice the information of one ranking stage,
    # so compare against a fit on the ranking duplicated.
    r2 = fit(["A", "B"], rankings=[RankingEvent(("A",), ("A", "B"), "c")] * 2, prior_scale=1.5)
    assert r.beta[0] > 0
    assert r2.beta[0] == pytest.approx(p.beta[0], abs=1e-6)


def test_matches_choix_without_position_bias() -> None:
    # Cross-check against an independent implementation (choix ILSR) on
    # symmetric data where gamma is zero by construction.
    rng = np.random.default_rng(3)
    ids = list("ABCDEF")
    truth = np.linspace(1.2, -1.2, 6)
    data, events = [], []
    for k, (i, j) in enumerate(itertools.permutations(range(6), 2)):
        for rep in range(6):
            win = rng.random() < 1 / (1 + np.exp(-(truth[i] - truth[j])))
            data.append((i, j) if win else (j, i))
            events.append(PairEvent(ids[i], ids[j], bool(win), f"c{k}"))
    ours = fit(ids, events, prior_scale=FLAT)
    theirs = choix.ilsr_pairwise(6, data, alpha=1e-4)
    theirs = theirs - theirs.mean()
    assert np.allclose(ours.beta, theirs, atol=0.15)
    assert abs(ours.gamma) < 0.2


def test_components_detects_disconnected_graph() -> None:
    comp = components(["A", "B", "C", "D"], _pairs("A", "B", 1, 1) + _pairs("C", "D", 1, 1), [])
    assert comp[0] == comp[1] != comp[2] == comp[3]


def test_mean_win_probability_bounds_and_symmetry() -> None:
    p = mean_win_probability(np.array([1.0, 0.0, -1.0]))
    assert p[1] == pytest.approx(0.5)
    assert p[0] + p[2] == pytest.approx(1.0)


def test_laplace_used_below_cluster_threshold() -> None:
    s = score(["A", "B", "C"], _pairs("A", "B", 3, 1)[:3] + _pairs("B", "C", 2, 1)[:2], draws=200)
    assert s.clusters < MIN_CLUSTERS and s.method == "laplace"


def test_bootstrap_used_with_enough_clusters_and_orders_ranks() -> None:
    events = []
    for c in range(40):
        events += [
            PairEvent("A", "B", True, f"c{c}"),
            PairEvent("B", "C", True, f"c{c}"),
            PairEvent("C", "A", c % 5 == 0, f"c{c}"),
        ]
    s = score(["A", "B", "C"], events, draws=200, top_k=1)
    assert s.method == "bootstrap"
    assert s.rank["A"] == 1 and s.rank["C"] == 3
    assert s.p_top_k["A"] > s.p_top_k["C"]
    lo, hi = s.rank_interval["A"]
    assert lo <= 1 <= hi
