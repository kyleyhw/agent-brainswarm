"""Read-side helpers over a run's ``data/`` folder, shared by pipeline and report."""

from __future__ import annotations

from agent_brainswarm.critique import CheckedCritique
from agent_brainswarm.models import Critique, IdeaCard, dump, load
from agent_brainswarm.state import Run


def cards(run: Run) -> dict[str, IdeaCard]:
    """Every idea card in the run, all versions, keyed by id."""
    if not run.exists("data", "cards.json"):
        return {}
    return {k: load(IdeaCard, v) for k, v in run.read("data", "cards.json").items()}


def latest(all_cards: dict[str, IdeaCard], idea: str) -> IdeaCard:
    """The most developed version of ``idea`` (follows parent links forward)."""
    current = all_cards[idea]
    while True:
        children = [c for c in all_cards.values() if c.parent_id == current.id]
        if not children:
            return current
        current = max(children, key=lambda c: c.version)


def root_id(all_cards: dict[str, IdeaCard], idea: str) -> str:
    """The version-1 ancestor of ``idea``."""
    card = all_cards[idea]
    while card.parent_id:
        card = all_cards[card.parent_id]
    return card.id


def load_checked(run: Run, name: str = "critiques.json") -> list[CheckedCritique]:
    """Critiques with their code flags, from ``data/<name>``."""
    if not run.exists("data", name):
        return []
    return [
        CheckedCritique(load(Critique, x["critique"]), x["quote_score"], tuple(x["flags"]))
        for x in run.read("data", name)
    ]


def store_checked(run: Run, checked: list[CheckedCritique], name: str = "critiques.json") -> None:
    """Write critiques with their flags to ``data/<name>``."""
    run.write(
        [
            {"critique": dump(c.critique), "quote_score": c.quote_score, "flags": list(c.flags)}
            for c in checked
        ],
        "data",
        name,
    )


def all_critiques(run: Run) -> list[CheckedCritique]:
    """First-round critiques plus every re-critique."""
    return load_checked(run) + load_checked(run, "recritiques.json")
