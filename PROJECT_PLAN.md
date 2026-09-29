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
    - [pending] Confirm in a fresh session that the hook fires for installed role agents (not picked up mid-session in a cloud session)
7.  [in-progress] Trigger behaviour: description excludes "brainstorm" (tested); live check needs a fresh session.
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
17. [in-progress] Live mini demo run on a concrete trading brief; record its outputs.
18. [pending] Offline replay demo (`examples/demo_run.py`) from the recording.
19. [completed] `install.py` (editable uv tool; symlink skill and agents).

## Phase 6: Evaluation
20. [pending] Benchmark: brainswarm versus a single strong agent asked for 20 ideas, on 3–5 briefs, judged by humans or by a measurable outcome.
21. [pending] Ablations: no critique, no workshop, no angle round.
22. [pending] Coverage study for the critique-stage bootstrap (~60 dispatches).
23. [pending] Recalibrate the size table from logged runs.

## Phase 7: Repeat runs and extensions
24. [completed] Idea library, lineage, new/variant/repeat tagging, returning champions, known-false ledger, feedback (fixture-tested).
25. [pending] External CLIs as generators; data-driven band-share defaults.
