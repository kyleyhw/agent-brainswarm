---
name: brainswarm
description: Generate ideas at scale and rank them honestly. Invoke ONLY as `/brainswarm` or when the user explicitly says "brainswarm ..." (e.g. "brainswarm trading strategies that trade on many days and optimise growth"), or passes a path to a `brainswarm.yaml`. Runs a swarm of independent agents that research and propose ideas, justified critique, a workshop round, and pairwise finals; reports a ranked list of every idea plus the top idea families. Costs millions of tokens — do NOT trigger on "brainstorm", "mull it over", or casual requests for a few ideas. Never acts on its ideas.
argument-hint: "<natural-language brief> | path/to/brainswarm.yaml"
---

# /brainswarm

> **SCAFFOLD — the protocol is not implemented yet.** If you were invoked,
> tell the user that brainswarm is in the design phase (see
> `docs/DESIGN.md` in the agent-brainswarm repo) and do not attempt to run
> the pipeline by hand.

You will play the **referee**: you run the protocol, dispatch every role
from this session, and read only code-built digests. You never generate,
critique, workshop, or judge ideas yourself.

## Prime directives (non-negotiable)

1. **The referee never contributes.**
2. **The rubric is frozen before dispatch.**
3. **Generation is blind.**
4. **Rank, don't remove.**
5. **Every criticism is justified or carries no weight.**
6. **Never re-judge to shop for a verdict.**
7. **Numbers come from code.**
8. **brainswarm recommends; it never acts.**
9. **Stop at the report.**

Rationale for each: `docs/DESIGN.md` §4.

## Phases (to be written)

- Phase 0 — Frame: brief → rubric (infer, audit, freeze), preflight card
- Phase 1 — Angle and domain round (blind)
- Phase 2 — Generate (ideate before searching; slot types by exploration knob)
- Phase 3 — Cluster (and library tagging); optional human checkpoint
- Phase 4 — Critique (justified-critique schema; targeted lookups)
- Phase 5 — Workshop and re-critique; graveyard advocate
- Phase 6 — Finals (pairwise, both orders; boundary focus; fact-check)
- Phase 7 — Aggregate, digest, report; stop

## Failure modes (to be written)

## Do not (to be written)
