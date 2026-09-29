"""Run configuration: size x exploration presets and ``brainswarm.yaml`` overrides.

The two knobs are independent (DESIGN.md §6). *Size* sets how much work is
done; *exploration* sets where it goes. Neither changes how ideas are judged.
Every numeric default is provisional; the basis for each is in DESIGN.md §6,
"Parameter provenance".
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, get_args

import numpy as np
import yaml

from agent_brainswarm.models import SchemaError

Size = Literal["quick", "standard", "deep"]
Exploration = Literal["conservative", "balanced", "wild"]

# (common, middle, rare) shares; also used for analogy distance (near, mid, far).
Shares = tuple[float, float, float]


@dataclass(frozen=True)
class RunConfig:
    """Every parameter a run uses. Built by :func:`build_config`, never by hand."""

    size: Size
    exploration: Exploration
    generators: int
    ideas_per_generator: int
    angles_per_generator: int
    domains_per_generator: int
    critics_per_idea: int
    critic_lookups: int
    generator_web_calls: int
    web: bool
    workshop_slots: int
    workshop_rounds: int
    recritique_critics: int
    finals_matches_per_idea: int
    top_k: int
    wildcards_shown: int
    returning_champions: int
    wave_size: int
    cards_per_critic: int
    pairs_per_judge: int
    draws: int
    prior_scale: float
    slot_mix: tuple[float, float, float]  # (angle, free, cross_domain)
    angle_bands: Shares
    distance_bands: Shares
    workshop_split: tuple[int, int, int]  # (value, wildcard, deepen) for the preset size
    generator_models: tuple[str, ...]
    critic_models: tuple[str, ...]
    judge_models: tuple[str, ...]
    checkpoint: bool
    seed: int
    judge_design: str = "crossover"  # see schedule.judge_batches


SIZE_PRESETS: dict[Size, dict[str, Any]] = {
    "quick": {
        "generators": 8,
        "workshop_slots": 0,
        "workshop_rounds": 0,
        "finals_matches_per_idea": 6,
    },
    "standard": {
        "generators": 20,
        "workshop_slots": 12,
        "workshop_rounds": 1,
        "finals_matches_per_idea": 8,
    },
    "deep": {
        "generators": 30,
        "workshop_slots": 16,
        "workshop_rounds": 2,
        "finals_matches_per_idea": 12,
    },
}

EXPLORATION_PRESETS: dict[Exploration, dict[str, Any]] = {
    "conservative": {
        "slot_mix": (0.70, 0.25, 0.05),
        "angle_bands": (0.60, 0.30, 0.10),
        "distance_bands": (0.60, 0.30, 0.10),
        "workshop_fractions": (8 / 12, 2 / 12, 2 / 12),
        "wildcards_shown": 1,
    },
    "balanced": {
        "slot_mix": (0.50, 0.25, 0.25),
        "angle_bands": (0.34, 0.33, 0.33),
        "distance_bands": (0.34, 0.33, 0.33),
        "workshop_fractions": (5 / 12, 4 / 12, 3 / 12),
        "wildcards_shown": 2,
    },
    "wild": {
        "slot_mix": (0.30, 0.20, 0.50),
        "angle_bands": (0.15, 0.35, 0.50),
        "distance_bands": (0.15, 0.35, 0.50),
        "workshop_fractions": (3 / 12, 7 / 12, 2 / 12),
        "wildcards_shown": 4,
    },
}

COMMON_DEFAULTS: dict[str, Any] = {
    "ideas_per_generator": 3,
    "angles_per_generator": 3,
    "domains_per_generator": 3,
    "critics_per_idea": 6,
    # Targeted lookups per critic *dispatch* (not per card): enough to check
    # the load-bearing citations of a ~6-card batch without researching.
    "critic_lookups": 10,
    # ~6 cards per critic dispatch keeps each critique context short and the
    # batch ranking reliable (long listwise rankings are position-dominated).
    "cards_per_critic": 6,
    # <= 10 ordered pairs per judge dispatch; the reverse order of each pair
    # goes to a different dispatch so no context sees both orders.
    "pairs_per_judge": 10,
    "generator_web_calls": 40,
    "web": True,
    "recritique_critics": 3,
    "top_k": 5,
    "returning_champions": 3,
    "wave_size": 10,
    "draws": 1000,
    # Prior beta ~ N(0, tau^2), tau = 1.5 logits: two ideas one prior sd apart
    # are separated by sigma(1.5) ~ 0.82 win probability, a plausible spread for
    # ideas answering the same brief. The ridge shrinks every strength, most
    # where data are scarce; sensitivity at tau/2 and 2*tau is reported.
    "prior_scale": 1.5,
    "generator_models": ("opus", "sonnet", "fable"),
    "critic_models": ("sonnet", "opus", "fable"),
    "judge_models": ("opus", "fable", "sonnet"),
    # Opt-in human checkpoint after clustering (DESIGN.md §3); off = autonomous.
    "checkpoint": False,
    "seed": None,
}

OVERRIDABLE = frozenset(COMMON_DEFAULTS) | {
    "generators",
    "workshop_slots",
    "workshop_rounds",
    "finals_matches_per_idea",
    "wildcards_shown",
    "slot_mix",
    "angle_bands",
    "distance_bands",
}


def largest_remainder(total: int, shares: tuple[float, ...]) -> tuple[int, ...]:
    """Split ``total`` integer units in proportion to ``shares``.

    Each part is ``floor(total * share)`` plus at most one extra unit; the
    extras go to the parts with the largest fractional remainders, so the
    parts sum to ``total`` exactly (DESIGN.md §6, "Banding and allocation").
    Ties in the remainder go to the earlier part, making the result
    deterministic.
    """
    weight = sum(shares)
    if total < 0 or weight <= 0:
        raise ValueError("total must be >= 0 and shares must have a positive sum")
    exact = [total * s / weight for s in shares]
    base = [int(x) for x in exact]
    leftover = total - sum(base)
    order = sorted(range(len(shares)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:leftover]:
        base[i] += 1
    return tuple(base)


def build_config(
    size: Size = "standard",
    exploration: Exploration = "balanced",
    overrides: Mapping[str, Any] | None = None,
    seed: int | None = None,
) -> RunConfig:
    """Combine the two presets, apply overrides, validate, and fix the seed."""
    problems: list[str] = []
    if size not in get_args(Size):
        problems.append(f"size {size!r} not one of {list(get_args(Size))}")
    if exploration not in get_args(Exploration):
        problems.append(f"exploration {exploration!r} not one of {list(get_args(Exploration))}")
    if problems:
        raise SchemaError(problems)
    values: dict[str, Any] = {**COMMON_DEFAULTS, **SIZE_PRESETS[size]}
    explore = dict(EXPLORATION_PRESETS[exploration])
    fractions = explore.pop("workshop_fractions")
    values.update(explore)
    for key, value in (overrides or {}).items():
        if key not in OVERRIDABLE:
            problems.append(f"unknown or non-overridable setting {key!r}")
        else:
            values[key] = tuple(value) if isinstance(value, list) else value
    if problems:
        raise SchemaError(problems)
    values["workshop_split"] = largest_remainder(values["workshop_slots"], fractions)
    if seed is not None:
        values["seed"] = seed
    if values["seed"] is None:
        # The seed is drawn from OS entropy by numpy and then recorded, so
        # every code-level random choice in the run can be replayed.
        values["seed"] = int(np.random.default_rng().integers(2**32))
    config = RunConfig(size=size, exploration=exploration, **values)
    _validate(config)
    return config


def _validate(config: RunConfig) -> None:
    problems: list[str] = []
    for name in ("slot_mix", "angle_bands", "distance_bands"):
        shares = getattr(config, name)
        if len(shares) != 3 or any(s < 0 for s in shares) or abs(sum(shares) - 1) > 1e-6:
            problems.append(f"{name} must be three non-negative shares summing to 1")
    positive = (
        "generators",
        "ideas_per_generator",
        "critics_per_idea",
        "finals_matches_per_idea",
        "cards_per_critic",
        "pairs_per_judge",
        "top_k",
    )
    for name in positive:
        if getattr(config, name) < 1:
            problems.append(f"{name} must be >= 1")
    if config.prior_scale <= 0:
        problems.append("prior_scale must be > 0 (the prior guarantees a finite, unique fit)")
    if problems:
        raise SchemaError(problems)


def config_to_dict(config: RunConfig) -> dict[str, Any]:
    """JSON-ready representation (tuples become lists)."""
    return {
        k: list(v) if isinstance(v, tuple) else v for k, v in dataclasses.asdict(config).items()
    }


def config_from_dict(data: Mapping[str, Any]) -> RunConfig:
    """Inverse of :func:`config_to_dict`."""
    fields = {f.name for f in dataclasses.fields(RunConfig)}
    data = {"judge_design": "split", **data}  # runs recorded before the field existed
    missing = fields - set(data)
    if missing:
        raise SchemaError([f"config missing {sorted(missing)}"])
    values: dict[str, Any] = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
    return RunConfig(**values)


def load_manifest(path: Path) -> tuple[str, RunConfig]:
    """Load ``brainswarm.yaml``: ``brief`` (required), ``size``, ``exploration``, ``overrides``."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("brief"), str):
        raise SchemaError([f"{path}: expected a mapping with a string 'brief'"])
    unknown = set(data) - {"brief", "size", "exploration", "overrides", "seed"}
    if unknown:
        raise SchemaError([f"{path}: unknown keys {sorted(unknown)}"])
    config = build_config(
        data.get("size", "standard"),
        data.get("exploration", "balanced"),
        data.get("overrides"),
        data.get("seed"),
    )
    return data["brief"], config
