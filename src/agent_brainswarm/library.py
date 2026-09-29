"""Per-project idea library across runs (DESIGN.md §8).

The library lives at ``home()/projects/<project>/`` and holds:

* ``library.json``: every idea from every run (latest version), with its
  run, cluster, final or preliminary standing, and open critiques;
* ``known_false.json``: claims refuted by fact-checks, dated;
* ``feedback.json``: what the owner did with ideas (the only ground truth).

History enters a run only *after* generation (DESIGN.md §7): the clusterer
sees the library index to tag new / variant / repeat, critics see the
known-false ledger, deepen slots come from library-related ideas, and
returning champions enter the finals. Generators never see it.
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any

from agent_brainswarm.models import IdeaCard, dump, load
from agent_brainswarm.state import Run, home, read_json, write_json

INDEX_LIMIT = 150  # most recent library ideas shown to the clusterer (context budget)
LEDGER_LIMIT = 50  # most recent refuted claims shown to critics


def _dir(run: Run) -> Any:
    return home() / "projects" / str(run.status.get("project", "default"))


def _load(run: Run, name: str) -> list[dict[str, Any]]:
    path = _dir(run) / name
    return list(read_json(path)) if path.exists() else []


def _save(run: Run, name: str, data: list[dict[str, Any]]) -> None:
    write_json(_dir(run) / name, data)


def _prior_entries(run: Run) -> list[dict[str, Any]]:
    """Library entries from runs other than this one."""
    return [e for e in _load(run, "library.json") if e.get("run") != run.root.name]


def index(run: Run) -> list[dict[str, str]]:
    """Compact index (id, title, pitch) for the clusterer."""
    entries = _prior_entries(run)[-INDEX_LIMIT:]
    return [
        {"id": e["id"], "title": e["card"]["title"], "pitch": e["card"]["pitch"]} for e in entries
    ]


def known_false(run: Run) -> list[str]:
    """Dated refuted claims for critics."""
    ledger = _load(run, "known_false.json")[-LEDGER_LIMIT:]
    return [f"{e['claim']} (refuted {e['date']}; {e.get('source', '')})" for e in ledger]


def import_champions(run: Run, n: int) -> list[str]:
    """Copy the library's top ``n`` finalists into this run's cards; return their ids."""
    if n <= 0:
        return []
    ranked = [e for e in _prior_entries(run) if e.get("mean_win") is not None and e.get("finalist")]
    ranked.sort(key=lambda e: -float(e["mean_win"]))
    if not ranked:
        return []
    cards = run.read("data", "cards.json")
    ids = []
    for e in ranked[:n]:
        card = load(IdeaCard, e["card"])
        champion = dataclasses.replace(card, id=e["id"], version=1, parent_id=None)
        cards[e["id"]] = dump(champion)
        ids.append(e["id"])
    run.write(cards, "data", "cards.json")
    run.write(ids, "data", "champions.json")
    return ids


def update(run: Run, entries: list[dict[str, Any]], refuted: list[dict[str, str]]) -> int:
    """Append this run's ideas and refuted claims; return the new library size."""
    library = [e for e in _load(run, "library.json") if e.get("run") != run.root.name]
    start = len(library)
    for i, e in enumerate(entries):
        library.append({**e, "id": f"L{start + i + 1:04d}", "run": run.root.name})
    _save(run, "library.json", library)
    if refuted:
        ledger = _load(run, "known_false.json")
        date = time.strftime("%Y-%m-%d")
        ledger += [{**r, "date": date, "run": run.root.name} for r in refuted]
        _save(run, "known_false.json", ledger)
    return len(library)


def record_feedback(run: Run, idea: str, status: str, note: str) -> None:
    """Store what the owner did with an idea."""
    fb = _load(run, "feedback.json")
    fb.append(
        {
            "run": run.root.name,
            "idea": idea,
            "status": status,
            "note": note,
            "date": time.strftime("%Y-%m-%d"),
        }
    )
    _save(run, "feedback.json", fb)
