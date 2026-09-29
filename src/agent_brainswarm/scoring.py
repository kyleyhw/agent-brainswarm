"""Strength estimation: penalised Bradley-Terry / Plackett-Luce with position bias.

Model (DESIGN.md §10). Each idea ``i`` has a strength ``beta_i``. A finals
verdict on the ordered pair (first, second) is won by ``first`` with
probability

    sigma(beta_first - beta_second + gamma),

where ``gamma`` is a global position-bias parameter (gamma > 0: judges
favour the idea shown first). Every verdict is used; position bias is
estimated rather than absorbed into ties.

A critic's truncated ranking ``rho_1 > ... > rho_k`` of its batch ``S`` is
Plackett-Luce, i.e. successive choices of the best remaining idea, stopping
after ``k`` choices:

    prod_{t=1..k} exp(beta_{rho_t}) / sum_{m in R_t} exp(beta_m),
    R_1 = S,  R_{t+1} = R_t minus {rho_t}.

Prior: beta_i, gamma ~ N(0, tau^2) independently, i.e. the penalised
log-likelihood l(theta) - ||theta||^2 / (2 tau^2). Each likelihood term is
concave and the penalty strictly concave, so Newton's method with step
halving converges to the unique maximiser (the MAP estimate). There
sum_i beta_i = 0 holds automatically: every term is invariant to adding a
constant to all betas, so the likelihood gradient sums to zero over the
betas, and stationarity forces sum_i beta_i / tau^2 = 0.

Uncertainty. With at least MIN_CLUSTERS dispatches, a cluster bootstrap
resamples whole dispatches (judgments within one subagent context are
correlated; across contexts they are treated as independent). With fewer,
draws come from the Laplace approximation N(theta_hat, (-H)^-1) of the
posterior, which the coverage study found reliable where the bootstrap
under-covered.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

# Newton stops when the largest parameter update is below this many logits;
# far below any difference that could change a reported rank.
TOLERANCE = 1e-9
MAX_ITERATIONS = 200
# A tier boundary falls where the tier leader beats the next idea in at
# least 95 % of draws (the conventional 5 % error rate, one-sided).
SEPARATION = 0.95
# The cluster bootstrap is used only with at least 30 clusters. In the
# coverage study (docs/studies/uncertainty_coverage.py) the dispatch
# bootstrap with ~20 clusters, the standard finals, covered the true rank
# only 90 % of the time when judgments within a dispatch were correlated,
# while the Laplace approximation covered 98-99 % in both scenarios.
MIN_CLUSTERS = 30


@dataclass(frozen=True)
class PairEvent:
    """One finals verdict: ``first`` was shown first; ``first_won`` says who won."""

    first: str
    second: str
    first_won: bool
    cluster: str


@dataclass(frozen=True)
class RankingEvent:
    """A truncated ranking ``order`` (best first) of the ideas in ``batch``."""

    order: tuple[str, ...]
    batch: tuple[str, ...]
    cluster: str


@dataclass(frozen=True)
class Fit:
    """MAP estimate and its curvature for one set of ideas."""

    ids: tuple[str, ...]
    beta: FloatArray
    gamma: float
    covariance: FloatArray  # (-H)^-1 over (beta, gamma)
    component: tuple[int, ...]


@dataclass(frozen=True)
class Scores:
    """Everything the report needs about one stratum of ideas."""

    fit: Fit
    method: Literal["bootstrap", "laplace"]
    draws: int
    clusters: int
    rank: dict[str, int]
    rank_interval: dict[str, tuple[int, int]]
    mean_win: dict[str, float]
    p_top_k: dict[str, float]
    tier: dict[str, int]
    unobserved_draw_fraction: float
    top_k_sensitivity: dict[str, tuple[str, ...]] = field(default_factory=dict)


def components(
    ids: Sequence[str], pairs: Sequence[PairEvent], rankings: Sequence[RankingEvent]
) -> tuple[int, ...]:
    """Connected components of the comparison graph (union-find).

    Strengths in different components are not comparable: the likelihood is
    unchanged if one component's betas shift relative to another's, and only
    the prior pins them. The report labels such ideas instead of ranking
    them against each other.
    """
    idx = {x: i for i, x in enumerate(ids)}
    parent = list(range(len(ids)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for p in pairs:
        parent[find(idx[p.first])] = find(idx[p.second])
    for r in rankings:
        members = [idx[x] for x in r.batch]
        for m in members[1:]:
            parent[find(m)] = find(members[0])
    roots: dict[int, int] = {}
    return tuple(roots.setdefault(find(i), len(roots)) for i in range(len(ids)))


class _Problem:
    """Pre-indexed likelihood terms for fast repeated evaluation."""

    def __init__(
        self,
        ids: Sequence[str],
        pairs: Sequence[PairEvent],
        rankings: Sequence[RankingEvent],
        prior_scale: float,
    ) -> None:
        idx = {x: i for i, x in enumerate(ids)}
        self.n = len(ids)
        self.dim = self.n + 1
        self.use_gamma = bool(pairs)
        self.precision = 1.0 / prior_scale**2
        # sign = +1 if the idea shown first won, else -1; the winner's
        # log-probability is log sigma(sign * (beta_first - beta_second + gamma)).
        self.pairs = [(idx[p.first], idx[p.second], 1.0 if p.first_won else -1.0) for p in pairs]
        self.stages: list[tuple[int, IntArray]] = []
        for r in rankings:
            remaining = [idx[x] for x in r.batch]
            for chosen in r.order:
                c = idx[chosen]
                self.stages.append((c, np.array(remaining, dtype=np.int64)))
                remaining.remove(c)

    def value(self, th: FloatArray) -> float:
        total = -0.5 * self.precision * float(th @ th)
        n = self.n
        for f, s, sign in self.pairs:
            total -= float(np.logaddexp(0.0, -sign * (th[f] - th[s] + th[n])))
        for c, rem in self.stages:
            total += float(th[c] - np.logaddexp.reduce(th[rem]))
        return total

    def derivatives(self, th: FloatArray) -> tuple[FloatArray, FloatArray]:
        n, dim = self.n, self.dim
        grad = -self.precision * th
        hess = -self.precision * np.eye(dim)
        for f, s, sign in self.pairs:
            x = sign * (th[f] - th[s] + th[n])
            q = 1.0 / (1.0 + np.exp(x))  # sigma(-x) = d/dx log sigma(x)
            a = np.zeros(dim)
            a[f], a[s], a[n] = sign, -sign, sign
            grad += q * a
            hess -= q * (1.0 - q) * np.outer(a, a)
        for c, rem in self.stages:
            z = th[rem] - th[rem].max()
            p = np.exp(z) / np.exp(z).sum()
            grad[rem] -= p
            grad[c] += 1.0
            hess[np.ix_(rem, rem)] -= np.diag(p) - np.outer(p, p)
        if not self.use_gamma:
            # No finals verdicts: gamma is not a parameter; pin it at 0.
            grad[n] = 0.0
            hess[n, :] = 0.0
            hess[:, n] = 0.0
            hess[n, n] = -self.precision
        return grad, hess

    def maximise(self, start: FloatArray | None = None) -> tuple[FloatArray, FloatArray]:
        theta = np.zeros(self.dim) if start is None else start.copy()
        if not self.use_gamma:
            theta[self.n] = 0.0
        for _ in range(MAX_ITERATIONS):
            grad, hess = self.derivatives(theta)
            step = np.linalg.solve(hess, -grad)
            base = self.value(theta)
            scale = 1.0
            while self.value(theta + scale * step) < base - 1e-12 and scale > 1e-8:
                scale *= 0.5
            theta = theta + scale * step
            if float(np.max(np.abs(scale * step))) < TOLERANCE:
                break
        _, hess = self.derivatives(theta)
        return theta, hess


def fit(
    ids: Sequence[str],
    pairs: Sequence[PairEvent] = (),
    rankings: Sequence[RankingEvent] = (),
    prior_scale: float = 1.5,
    start: FloatArray | None = None,
) -> Fit:
    """MAP estimate of (beta, gamma) and the Laplace covariance at it."""
    problem = _Problem(ids, pairs, rankings, prior_scale)
    theta, hess = problem.maximise(start)
    n = len(ids)
    return Fit(
        ids=tuple(ids),
        beta=theta[:n].copy(),
        gamma=float(theta[n]),
        covariance=np.linalg.inv(-hess),
        component=components(ids, pairs, rankings),
    )


def mean_win_probability(beta: FloatArray) -> FloatArray:
    """``pbar_i = (1/(N-1)) sum_{j != i} sigma(beta_i - beta_j)``: mean win chance vs the field."""
    n = len(beta)
    if n < 2:
        return np.full(n, 0.5)
    prob = 1.0 / (1.0 + np.exp(-(beta[:, None] - beta[None, :])))
    np.fill_diagonal(prob, 0.0)
    return prob.sum(axis=1) / (n - 1)


def ranks_of(beta: FloatArray) -> IntArray:
    """1-based ranks, best first; ties broken by position (stable)."""
    order = np.argsort(-beta, kind="stable")
    ranks = np.empty(len(beta), dtype=np.int64)
    ranks[order] = np.arange(1, len(beta) + 1)
    return ranks


def top_k_set(ids: Sequence[str], beta: FloatArray, k: int) -> tuple[str, ...]:
    """The ids of the ``k`` strongest ideas, best first."""
    order = np.argsort(-beta, kind="stable")[:k]
    return tuple(ids[int(i)] for i in order)


def score(
    ids: Sequence[str],
    pairs: Sequence[PairEvent] = (),
    rankings: Sequence[RankingEvent] = (),
    prior_scale: float = 1.5,
    draws: int = 1000,
    top_k: int = 5,
    seed: int = 0,
    method: Literal["auto", "bootstrap", "laplace"] = "auto",
) -> Scores:
    """Fit, draw uncertainty (bootstrap or Laplace), and summarise per idea.

    ``method="auto"`` bootstraps with at least MIN_CLUSTERS clusters and uses
    the Laplace approximation otherwise; the explicit values exist for the
    coverage study.
    """
    ids = tuple(ids)
    n = len(ids)
    full = fit(ids, pairs, rankings, prior_scale)
    rng = np.random.default_rng(seed)
    clusters = sorted({p.cluster for p in pairs} | {r.cluster for r in rankings})
    unobserved = 0
    use_bootstrap = method == "bootstrap" or (method == "auto" and len(clusters) >= MIN_CLUSTERS)
    if use_bootstrap and clusters:
        chosen: Literal["bootstrap", "laplace"] = "bootstrap"
        by_pairs: dict[str, list[PairEvent]] = {c: [] for c in clusters}
        by_ranks: dict[str, list[RankingEvent]] = {c: [] for c in clusters}
        for p in pairs:
            by_pairs[p.cluster].append(p)
        for r in rankings:
            by_ranks[r.cluster].append(r)
        start = np.append(full.beta, full.gamma)
        samples = np.empty((draws, n))
        for b in range(draws):
            picked = [clusters[int(k)] for k in rng.integers(len(clusters), size=len(clusters))]
            bp = [p for c in picked for p in by_pairs[c]]
            br = [r for c in picked for r in by_ranks[c]]
            seen = {x for p in bp for x in (p.first, p.second)} | {x for r in br for x in r.batch}
            if len(seen) < n:
                unobserved += 1
            samples[b] = fit(ids, bp, br, prior_scale, start=start).beta
    else:
        chosen = "laplace"
        mean = np.append(full.beta, full.gamma)
        samples = rng.multivariate_normal(mean, full.covariance, size=draws)[:, :n]

    point_ranks = ranks_of(full.beta)
    sample_ranks = np.array([ranks_of(row) for row in samples])
    lo = np.percentile(sample_ranks, 2.5, axis=0, method="lower")
    hi = np.percentile(sample_ranks, 97.5, axis=0, method="higher")
    k = min(top_k, n)
    p_top = (sample_ranks <= k).mean(axis=0)
    separation = (samples[:, :, None] > samples[:, None, :]).mean(axis=0)

    tier = np.zeros(n, dtype=np.int64)
    order = [int(i) for i in np.argsort(-full.beta, kind="stable")]
    current, leader = 1, order[0] if order else 0
    for pos, i in enumerate(order):
        if pos > 0 and separation[leader, i] >= SEPARATION:
            current += 1
            leader = i
        tier[i] = current

    sensitivity = {
        f"tau={prior_scale * factor:g}": top_k_set(
            ids, fit(ids, pairs, rankings, prior_scale * factor).beta, k
        )
        for factor in (0.5, 1.0, 2.0)
    }
    mean_win = mean_win_probability(full.beta)
    return Scores(
        fit=full,
        method=chosen,
        draws=draws,
        clusters=len(clusters),
        rank={x: int(point_ranks[i]) for i, x in enumerate(ids)},
        rank_interval={x: (int(lo[i]), int(hi[i])) for i, x in enumerate(ids)},
        mean_win={x: float(mean_win[i]) for i, x in enumerate(ids)},
        p_top_k={x: float(p_top[i]) for i, x in enumerate(ids)},
        tier={x: int(tier[i]) for i, x in enumerate(ids)},
        unobserved_draw_fraction=unobserved / draws,
        top_k_sensitivity=sensitivity,
    )
