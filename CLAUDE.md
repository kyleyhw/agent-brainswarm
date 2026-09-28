# agent-brainswarm — notes for Claude

- `docs/DESIGN.md` is the source of truth. Update it when a design decision
  changes; do not let code drift from it.
- Status: design phase. Do not implement protocol logic until the owner
  gives an explicit go for that stage (see DESIGN.md §18 build order).
- Conventions follow agent-evolve (github.com/kyleyhw/agent-evolve): SKILL.md
  files are the most important deliverable; rules that matter are also
  enforced in code; frozen dataclasses; inline rationale; dated test reports
  under `tests/reports/`; itemised commit messages.
- The skill is `/brainswarm`, invoked by "brainswarm ...". It must never
  trigger on "brainstorm".
- brainswarm never imports or requires agent-evolve; the link is export files.
