# Project Development Plan
This document outlines the planned phases and tasks for developing agent-brainswarm. The design they implement is specified in [`docs/DESIGN.md`](docs/DESIGN.md).

## Phase 1: Design and scaffold
1.  [completed] Research prior art (skillsarena.ai, zhjai/agent-arena, oyi77/agent-arena-skill) and agent-evolve conventions.
2.  [completed] Design discussion and decisions recorded in `docs/DESIGN.md`.
3.  [completed] Scaffold: skill and role stubs, package skeleton, scaffold tests.
4.  [completed] Toolchain and documentation compliance (`uv`, `ruff`, `ty`, secret scanning, `pre-commit` hooks; README; references; test report).
5.  [completed] Independent critique of `docs/DESIGN.md` by Fable and Opus subagents; dispositions recorded in `DESIGN.md` §21.

## Phase 2: Verification of platform assumptions
6.  [completed] Per-role tool restriction (`DESIGN.md` §16.1).
    - [completed] Documentation: agent allowlists are enforced; agents may declare hooks in frontmatter
    - [completed] `brainswarm guard` hook implemented and tested through its stdin / exit-code interface
    - [completed] Live: the hook fires for role agents (probe dispatch: 5 of 5 calls allowed or blocked as designed)
    - [completed] Fail closed: a missing CLI or a guard crash now blocks instead of allowing (regression tests)
    - [completed] Found live: project-level agent hooks do not run without workspace trust (fresh cloud session); referee guard self-test added
    - [completed] Role files moved to `agents/` and linked user-level by `install.py`, so their guard hook always runs
7.  [completed] Trigger behaviour, live in fresh cloud sessions: skill and role agents load; "brainstorm" does not trigger; "brainswarm" triggered only after the description was rewritten to lead with the trigger (evidence indirect, from token accounting).
8.  [completed] Transcript token accounting: message-id dedupe; output tokens estimated where final usage is missing.
9.  [completed] Finals uncertainty with few clusters: coverage study (`docs/studies/uncertainty_coverage.py`); Laplace below 30 clusters.

## Phase 3: Python layer with fixture mode
10. [completed] `models`, `config`, `rubric`.
11. [completed] `assign`, `critique`, `schedule`.
12. [completed] `scoring` (Bradley–Terry, Plackett–Luce, position bias, Laplace and bootstrap, tiers, P(top-k)), `select`.
13. [completed] `pipeline` state machine, `state`, `records`, `usage`, `report`, `export`, `sandbox`, `guard`, `cli`.
14. [completed] Fixture mode: deterministic fake agents drive full runs; tests and test reports.

## Phase 4: Protocol prompts
15. [completed] `/brainswarm` referee `SKILL.md`.
16. [completed] Role agents: ideator, generator, clusterer, critic, checker, advocate, workshop, judge, rubric auditor.

## Phase 5: Demo and installation
17. [completed] Live mini demo run on a concrete trading brief; recorded in `examples/demo-run/`.
    - [completed] Manifests for two physically checkable briefs in `examples/demos/` (exoplanet-transit setup; home heating)
    - [pending] Live runs of the two new manifests (shelved until usage allows)
18a. [completed] README and example tour rewritten around one real run (pipeline figure, one idea's path, ranking figure, use cases, limits); rerun analysis moved to `docs/studies/position_bias.md`.
18b. [pending] Showcase demos, shelved until usage allows (new-token estimates at reduced size):
    - [pending] Home heating, web on, as the flagship the README tour is rebuilt around (~2–3M)
    - [pending] Make this repo's test suite faster without losing coverage, exported to agent-evolve with a measured metric (~1.5M)
    - [pending] Home heating at `conservative` vs `wild`, to show the exploration setting (2 × ~1.5M)
    - [pending] Home heating run twice, to show the idea library across runs (~1.5M)
    - [pending] Exoplanet-transit setup, web on (~2–3M)
    - [completed] Controlled rerun of the ETF demo from the workshop and from the finals with the fixes; crossover judge experiment
18. [completed] Offline replay demo (`examples/demo_run.py`); reproduces the ranking exactly.
19. [completed] `install.py` (editable uv tool; symlink skill and agents).

## Phase 6: Evaluation
20. [in-progress] Benchmark: brainswarm versus a single strong agent asked for 20 ideas, on 3–5 briefs, judged by humans or by a measurable outcome ([`docs/BENCHMARK.md`](docs/BENCHMARK.md)).
    - [completed] Protocol, blinded pack builder, ETF baseline and pack
    - [completed] ETF pack rated by six counterbalanced LLM reviewers: no preference between the sides (docs/BENCHMARK.md)
    - [pending] Exoplanet and home-heating briefs (need their brainswarm runs)
21. [pending] Ablations: no critique, no workshop, no angle round.
22. [pending] Coverage study for the critique-stage bootstrap (~60 dispatches).
23. [completed] Recalibrate the size table from logged runs (`docs/studies/token_calibration.py`): ~4–6M / ~10–15M / ~16–23M new tokens.
    - [pending] Replace the web-on ranges with measurements from a run with web research on

## Phase 7: Repeat runs and extensions
24. [completed] Idea library, lineage, new/variant/repeat tagging, returning champions, known-false ledger, feedback (fixture-tested).
25. [pending] External CLIs as generators; data-driven band-share defaults.
26. [pending] Re-critique checks that each claimed fix is in the developed card (every critique was answered as fixed in both workshops).
27. [pending] Measure workshop variance at standard size (two attempts reversed the demo's finals order).
