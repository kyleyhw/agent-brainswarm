# agent-brainswarm — notes for Claude

- `docs/DESIGN.md` is the source of truth for the design; `PROJECT_PLAN.md`
  tracks phases and task status. Update both when a decision or status
  changes.
- Status: design phase. Do not implement protocol logic until the owner
  gives an explicit go for that phase.
- Commits are authored as the owner with no AI attribution trailers or
  footers (no `Co-Authored-By`, no "Generated with").
- Conventions follow agent-evolve (github.com/kyleyhw/agent-evolve): SKILL.md
  files are the most important deliverable; rules that matter are also
  enforced in code; frozen dataclasses; inline rationale; dated test
  reports under `tests/reports/`.
- Toolchain: `uv`, `ruff`, `ty`, `detect-secrets`, `pre-commit`
  (`uv run pre-commit install`).
- The skill is `/brainswarm`, invoked by "brainswarm ...". It must never
  trigger on "brainstorm".
- brainswarm never imports or requires agent-evolve; the link is export files.
