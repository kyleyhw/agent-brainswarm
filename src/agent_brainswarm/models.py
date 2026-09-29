"""Frozen dataclasses for everything that crosses the agent/code boundary.

Agents write JSON files; code loads them through :func:`load`, which checks
required fields, ``Literal`` values and nested dataclasses, and converts
lists to tuples so every loaded object is immutable. A malformed file raises
:class:`SchemaError` listing every problem at once, so the referee can send a
single corrective retry to the agent that wrote it (DESIGN.md §16.5).
"""

from __future__ import annotations

import dataclasses
import types
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Union, get_args, get_origin

Severity = Literal["fatal", "major", "minor"]
CriterionKind = Literal["gate", "judged", "measured"]
SlotType = Literal["angle", "free", "cross_domain"]
Band = Literal["common", "middle", "rare"]
Distance = Literal["near", "mid", "far"]
Transfer = Literal["strong", "partial", "stretch"]
Resolution = Literal["open", "fixed", "rebutted", "conceded"]
Preferred = Literal["first", "second"]
LibraryRelation = Literal["new", "variant", "repeat"]


class SchemaError(ValueError):
    """Raised when agent output does not match the expected schema."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("; ".join(problems))


@dataclass(frozen=True)
class Criterion:
    """One rubric criterion (DESIGN.md §5, Phase 0)."""

    name: str
    kind: CriterionKind
    definition: str
    anchors: tuple[str, ...] = ()
    command: str | None = None
    user_stated: bool = False


@dataclass(frozen=True)
class Rubric:
    """The frozen rubric: brief, criteria, and the referee's assumptions."""

    brief: str
    criteria: tuple[Criterion, ...]
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Angle:
    """An approach angle (or far domain) proposed blind in Phase 1."""

    id: str
    proposer: str
    text: str
    kind: Literal["angle", "domain"] = "angle"
    distance: Distance | None = None


@dataclass(frozen=True)
class Provenance:
    """Where an idea came from; used for yield analysis (DESIGN.md §14)."""

    generator_id: str
    model: str
    slot_type: SlotType
    angle_id: str | None = None
    band: Band | None = None
    transfer: Transfer | None = None
    research_derived: bool = False


@dataclass(frozen=True)
class IdeaCard:
    """A structured idea (DESIGN.md §5, Phase 2)."""

    id: str
    title: str
    pitch: str
    mechanism: str
    rationale: str
    assumptions: tuple[str, ...]
    failure_modes: tuple[str, ...]
    cheapest_test: str
    effort: str
    provenance: Provenance
    sources: tuple[str, ...] = ()
    spec: str | None = None
    version: int = 1
    parent_id: str | None = None

    def text(self) -> str:
        """All prose fields joined; the corpus critique targets are matched against."""
        parts = [self.title, self.pitch, self.mechanism, self.rationale, self.cheapest_test]
        parts += [self.effort, *self.assumptions, *self.failure_modes, self.spec or ""]
        return "\n".join(p for p in parts if p)


@dataclass(frozen=True)
class CardDraft:
    """An idea card as an agent writes it; code adds id and provenance."""

    title: str
    pitch: str
    mechanism: str
    rationale: str
    assumptions: tuple[str, ...]
    failure_modes: tuple[str, ...]
    cheapest_test: str
    effort: str
    sources: tuple[str, ...] = ()
    spec: str | None = None
    raw_index: int | None = None
    transfer: Transfer | None = None


@dataclass(frozen=True)
class Critique:
    """One justified critique item (DESIGN.md §5, Phase 4)."""

    id: str
    idea_id: str
    critic_id: str
    critic_model: str
    target: str
    mechanism: str
    evidence: str
    severity: Severity
    falsifier: str
    gate: str | None = None
    resolution: Resolution = "open"


@dataclass(frozen=True)
class Ranking:
    """A critic's best-to-worst ordering of the ideas it reviewed."""

    critic_id: str
    critic_model: str
    order: tuple[str, ...]
    criterion: str = "overall"


@dataclass(frozen=True)
class Rating:
    """A critic's coarse 1-5 upside / probability ratings, used only to pick wildcards."""

    critic_id: str
    idea_id: str
    upside: int
    probability: int


@dataclass(frozen=True)
class Match:
    """One finals comparison in one presentation order."""

    judge_id: str
    judge_model: str
    first: str
    second: str
    preferred: Preferred
    criterion: str = "overall"
    reason: str = ""


def load[T](cls: type[T], data: Any, where: str = "") -> T:
    """Build a frozen dataclass from a JSON mapping, validating as it goes."""
    problems: list[str] = []
    obj = _load(cls, data, where or cls.__name__, problems)
    if problems:
        raise SchemaError(problems)
    return typing.cast(T, obj)


def dump(obj: object) -> Any:
    """Convert a dataclass (or nested structure of them) to JSON-ready data."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: dump(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, tuple | list):
        return [dump(x) for x in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    return obj


def _load(cls: Any, data: Any, where: str, problems: list[str]) -> object | None:
    if not isinstance(data, Mapping):
        problems.append(f"{where}: expected an object, got {type(data).__name__}")
        return None
    hints = typing.get_type_hints(cls)
    known = {f.name for f in dataclasses.fields(cls)}
    for extra in sorted(set(data) - known):
        problems.append(f"{where}: unknown field '{extra}'")
    kwargs: dict[str, object] = {}
    before = len(problems)
    for f in dataclasses.fields(cls):
        has_default = (
            f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING
        )
        if f.name not in data:
            if not has_default:
                problems.append(f"{where}: missing field '{f.name}'")
            continue
        kwargs[f.name] = _coerce(hints[f.name], data[f.name], f"{where}.{f.name}", problems)
    if len(problems) > before:
        return None
    return cls(**kwargs)


def _coerce(tp: Any, value: Any, where: str, problems: list[str]) -> object:
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        options = get_args(tp)
        if value is None and type(None) in options:
            return None
        non_none = [t for t in options if t is not type(None)]
        return _coerce(non_none[0], value, where, problems)
    if origin is Literal:
        allowed = get_args(tp)
        if value not in allowed:
            problems.append(f"{where}: {value!r} not one of {list(allowed)}")
        return value
    if origin is tuple:
        if not isinstance(value, list | tuple):
            problems.append(f"{where}: expected a list")
            return ()
        item_tp = get_args(tp)[0]
        return tuple(_coerce(item_tp, v, f"{where}[{i}]", problems) for i, v in enumerate(value))
    if dataclasses.is_dataclass(tp):
        return _load(typing.cast(type, tp), value, where, problems)
    if tp is bool:
        if not isinstance(value, bool):
            problems.append(f"{where}: expected true/false")
        return value
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"{where}: expected an integer")
        return value
    if tp is str:
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}: expected a non-empty string")
        return value
    return value
