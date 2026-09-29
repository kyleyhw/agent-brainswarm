"""Justified-critique checks (DESIGN.md §5, Phase 4).

Code enforces what it can decide mechanically:

* **Schema**: every field present and non-empty (via :mod:`models`).
* **Quote match**: ``target`` must be a quote from the card it attacks.
* **"Unproven" alone is inadmissible**: a mechanism that only says the idea
  is untested, with no failure mechanism, is flagged.
* **Repetition**: one critic making nearly the same point about 3+ ideas is
  flagged as templated.

The *substitution test* ("would this critique be equally true of a random
other idea?") needs judgment and is done by the checker role; its verdicts
are merged here. Flagged critiques are kept and shown but carry no weight.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from agent_brainswarm.models import Critique, SchemaError, load

# A quote may differ slightly from the card (an elided word, changed
# punctuation). One changed word in a 7-word quote gives a SequenceMatcher
# ratio of ~0.86, so 0.85 accepts that and rejects paraphrase.
QUOTE_MATCH = 0.85
# "Unproven" critiques: fewer than 8 words beyond the unproven phrase leave
# no room for a failure mechanism (subject + verb + cause is ~8 words).
UNPROVEN_MIN_WORDS = 8
UNPROVEN = re.compile(
    r"\b(unproven|untested|not (been )?(proven|tested|validated)|no evidence|lacks evidence|"
    r"speculative)\b",
    re.IGNORECASE,
)
# Two mechanisms by one critic are "the same point" above this ratio; set
# below QUOTE_MATCH because templated critiques vary their nouns.
REPETITION_MATCH = 0.8
REPETITION_MIN_IDEAS = 3


def _normalise(text: str) -> list[str]:
    return re.sub(r"[^\w\s%.-]", " ", text.lower()).split()


def quote_match(target: str, text: str) -> float:
    """Best similarity between ``target`` and any same-length window of ``text``."""
    t_words, words = _normalise(target), _normalise(text)
    if not t_words:
        return 0.0
    joined_t, joined = " ".join(t_words), " ".join(words)
    if joined_t in joined:
        return 1.0
    width = len(t_words)
    best = 0.0
    for start in range(max(1, len(words) - width + 1)):
        window = " ".join(words[start : start + width])
        best = max(best, SequenceMatcher(None, joined_t, window).ratio())
    return best


def unproven_only(mechanism: str) -> bool:
    """True if the mechanism is essentially "this is unproven" and nothing more."""
    if not UNPROVEN.search(mechanism):
        return False
    remainder = UNPROVEN.sub(" ", mechanism)
    return len(_normalise(remainder)) < UNPROVEN_MIN_WORDS


@dataclass(frozen=True)
class CheckedCritique:
    """A schema-valid critique plus the mechanical flags code attached to it."""

    critique: Critique
    quote_score: float
    flags: tuple[str, ...]

    @property
    def counts(self) -> bool:
        """Whether the critique carries weight (no disqualifying flag)."""
        return not self.flags


def check_items(
    items: Sequence[Mapping[str, Any]],
    card_texts: Mapping[str, str],
    where: str,
) -> tuple[list[CheckedCritique], list[str]]:
    """Validate one critic dispatch's critique items; return checked items and problems.

    Items attacking an idea outside the dispatch's batch are schema problems
    (the critic was not shown that card); a quote that does not match is a
    flag, not a rejection, so the item is still visible in the report.
    """
    checked: list[CheckedCritique] = []
    problems: list[str] = []
    for i, raw in enumerate(items):
        try:
            c = load(Critique, raw, f"{where}.critiques[{i}]")
        except SchemaError as err:
            problems += err.problems
            continue
        if c.idea_id not in card_texts:
            problems.append(f"{where}.critiques[{i}]: idea {c.idea_id!r} is not in this batch")
            continue
        score = quote_match(c.target, card_texts[c.idea_id])
        flags: list[str] = []
        if score < QUOTE_MATCH:
            flags.append("target_not_in_card")
        if unproven_only(c.mechanism):
            flags.append("unproven_only")
        checked.append(CheckedCritique(c, round(score, 3), tuple(flags)))
    return checked, problems


def repetition_flags(critiques: Iterable[Critique]) -> set[str]:
    """Ids of critiques whose critic made nearly the same point about 3+ ideas."""
    by_critic: dict[str, list[Critique]] = defaultdict(list)
    for c in critiques:
        by_critic[c.critic_id].append(c)
    flagged: set[str] = set()
    for items in by_critic.values():
        for c in items:
            similar = {
                o.idea_id
                for o in items
                if SequenceMatcher(None, c.mechanism.lower(), o.mechanism.lower()).ratio()
                >= REPETITION_MATCH
            }
            if len(similar) >= REPETITION_MIN_IDEAS:
                flagged.add(c.id)
    return flagged


def merge_flags(
    checked: Sequence[CheckedCritique],
    repetition: set[str],
    substitution_generic: set[str],
) -> list[CheckedCritique]:
    """Attach repetition and substitution-test flags to the checked critiques."""
    out: list[CheckedCritique] = []
    for item in checked:
        flags = list(item.flags)
        if item.critique.id in repetition:
            flags.append("repetitive")
        if item.critique.id in substitution_generic:
            flags.append("generic")
        out.append(CheckedCritique(item.critique, item.quote_score, tuple(flags)))
    return out
