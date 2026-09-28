# Project Development Plan
This document outlines the planned phases and tasks for developing agent-brainswarm. The design they implement is specified in [`docs/DESIGN.md`](docs/DESIGN.md).

## Phase 1: Design and scaffold
1.  [completed] Research prior art (skillsarena.ai, zhjai/agent-arena, oyi77/agent-arena-skill) and agent-evolve conventions.
2.  [completed] Design discussion and decisions recorded in `docs/DESIGN.md`.
3.  [completed] Scaffold: skill and role stubs, package skeleton, scaffold tests.
4.  [completed] Toolchain and documentation compliance.
    - [completed] `uv` project with `uv.lock`; `ruff`, `ty`, `detect-secrets`, `pre-commit` as dev dependencies
    - [completed] `.gitignore` entries for `.env`, `.DS_Store`, `venv/`, `.venv/`
    - [completed] README with directory tree, documentation index, logic and mathematics
    - [completed] References section in `docs/DESIGN.md`
    - [completed] Scaffold test report
5.  [pending] Independent critique of `docs/DESIGN.md` by Fable and Opus subagents; merge accepted changes.

## Phase 2: Verification of platform assumptions
6.  [pending] Per-role tool restriction in Claude Code (`DESIGN.md` §16.1).
    - [pending] Confirm agent-definition tool allowlists are enforced for subagents
    - [pending] Restrict generator shell use to the sandbox wrapper
7.  [pending] Trigger behaviour: `/brainswarm` fires on "brainswarm …", never on "brainstorm", and does not collide with `/evolve`.
8.  [pending] Transcript token accounting: fields, message-id dedupe, output-token reliability.
9.  [pending] Bootstrap design for few judges in the finals (`DESIGN.md` §16.11).

## Phase 3: Python layer with fixture mode
10. [pending] `models`, `config` (size × exploration presets, overrides), `rubric` (freeze and hash).
11. [pending] `assign` (banding, stratified allocation), `critique` (schema, quote match, generic filter).
12. [pending] `scoring` (Bradley–Terry, Plackett–Luce, clustered bootstrap, tiers), `select` (family-aware top-k, slots).
13. [pending] `state` (run folder, checkpoints, resume), `usage`, `report`, `export`, `sandbox`, `cli`.
14. [pending] Fixture mode: canned agent outputs drive the full pipeline at zero token cost; tests and test reports.

## Phase 4: Protocol prompts
15. [pending] `/brainswarm` referee SKILL.md (prime directives, phases, failure modes, "do not" list).
16. [pending] Role prompts for generator, clusterer, critic, advocate, workshop, judge, rubric auditor.

## Phase 5: Demo and installation
17. [pending] Tier 2 live mini demo run; record its output.
18. [pending] Tier 1 offline replay demo (`examples/demo_run.py`) from the recording.
19. [pending] `install.py` (symlink skill and agents into `~/.claude/`), usage documentation.

## Phase 6: Evaluation
20. [pending] Benchmark: brainswarm versus a single strong agent asked for 20 ideas, on 3–5 briefs.
21. [pending] Ablations: no critique, no workshop, no angle round.
22. [pending] Dated benchmark reports; recalibrate the size table from logged actuals.

## Phase 7: Repeat runs and extensions
23. [pending] Idea library, lineage, new/variant/repeat tagging, returning champions.
24. [pending] External CLIs as generators; data-driven band-mix defaults.
