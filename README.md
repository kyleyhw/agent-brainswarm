# agent-brainswarm

A multi-agent idea generation and ranking system built as a Claude Code
skill. Written with the goal of producing diverse, rigorously critiqued
ideas that can be handed to [agent-evolve](https://github.com/kyleyhw/agent-evolve)
for testing and improvement.

> **Status: design phase.** The protocol is specified in
> [`docs/DESIGN.md`](docs/DESIGN.md) and the work is tracked in
> [`PROJECT_PLAN.md`](PROJECT_PLAN.md). The repository currently holds a
> scaffold only; `/brainswarm` reports that it is not implemented yet.

Like agent-evolve, this is a skills bundle installed once and used across
projects. The commands below are instructions given to Claude, not shell
commands:

```
brainswarm trading strategies that trade on many days and optimise growth and diversification
brainswarm ways to cut our CI time — quick, surprise me
/brainswarm path/to/brainswarm.yaml
```

**brainswarm the ideas, evolve the code.**

## Documentation

| Document | Content |
|---|---|
| [`docs/DESIGN.md`](docs/DESIGN.md) | Full design specification: purpose, pipeline, knobs, scoring, privacy, security, logging, watch list, references |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Development phases and task status |
| [`tests/reports/`](tests/reports/) | Dated test reports |
| [`examples/README.md`](examples/README.md) | Planned demos |

## Directory structure

```
agent-brainswarm/
├── .claude/
│   ├── skills/brainswarm/SKILL.md   # /brainswarm: the referee (user-facing skill)
│   └── agents/brainswarm-*.md       # role definitions with tool allowlists
│                                    #   generator, clusterer, critic, advocate,
│                                    #   workshop, judge, rubric-auditor
├── src/agent_brainswarm/            # Python "hands": enforcement, scoring, reports
│   ├── models.py  config.py  rubric.py  assign.py  critique.py
│   ├── library.py  scoring.py  select.py  sandbox.py  usage.py
│   └── state.py  report.py  export.py  cli.py
├── docs/DESIGN.md                   # design specification
├── examples/                        # demo brief, config, recorded run (planned)
├── tests/
│   ├── test_scaffold.py
│   └── reports/                     # dated test reports
├── PROJECT_PLAN.md
├── CLAUDE.md                        # repository notes for Claude sessions
├── pyproject.toml  uv.lock          # uv-managed project
├── .pre-commit-config.yaml          # ruff, ruff-format, detect-secrets, ty
└── .secrets.baseline                # detect-secrets baseline
```

## Main logic

A run is a fixed sequence of phases. The session running `/brainswarm`
acts as a referee that dispatches every role and never contributes ideas
or judgments itself.

```
Frame ─ Angle & domain round ─ Generate ─ Cluster ─ Critique
      ─ Workshop + re-critique ─ Finals ─ Aggregate & report ─ stop
```

1. **Frame.** The brief is turned into a rubric (gates, judged criteria,
   optional measured criteria), audited by a separate agent, and frozen by
   hash before any agent is dispatched.
2. **Angle and domain round.** Each generator blindly proposes approach
   angles and distant domains; code bands them by popularity and distance.
3. **Generate.** ~20 generators (standard size) each write 3 idea cards,
   ideating before searching the web, then researching and sanity-checking
   in a sandbox. Generation never sees other generators' ideas or earlier
   runs, to prevent design fixation.
4. **Cluster.** Near-duplicates merge; variants are kept as siblings;
   ideas are tagged against the idea library.
5. **Critique.** ~6 critics per idea write justified critiques (quoted
   target, mechanism, evidence, severity, falsifier); generic critiques are
   down-weighted by code.
6. **Workshop.** Top-value, wildcard and deepen slots are developed into a
   second version that answers every serious critique, then re-critiqued.
7. **Finals.** Pairwise matches judged in both orders by a mixed-model
   panel.
8. **Report.** Every idea is ranked with uncertainty; the top idea families
   (default 5) and labelled wildcards are highlighted; nothing is removed.

Two independent knobs control a run: **size** (`quick` / `standard` /
`deep`, trading tokens for thoroughness) and **exploration**
(`conservative` / `balanced` / `wild`, shifting where effort goes without
changing its cost). Neither knob changes how ideas are judged.

### Scoring model

Pairwise outcomes are modelled with the Bradley–Terry model
[[1]](docs/DESIGN.md#ref-bradley-terry-1952). Each idea $i$ has a latent
strength $\beta_i$, and

$$
P(i \succ j) = \sigma(\beta_i - \beta_j), \qquad \sigma(x) = \frac{1}{1 + e^{-x}},
$$

with the identifiability constraint $\sum_i \beta_i = 0$. Critics' batch
rankings enter through the Plackett–Luce extension. The reported quantity
is $\sigma(\beta_i)$, the probability of beating a hypothetical idea of
average strength. Uncertainty comes from a bootstrap that resamples judges
(clusters of correlated judgments) and refits $\beta$; ideas whose rank
intervals overlap are reported as one tier. Derivations and caveats are in
[`docs/DESIGN.md` §10](docs/DESIGN.md#10-scoring).

### Slot assignment

Generator slots in a band $b$ (common, middle, rare) are allocated as
$n_b = \operatorname{round}(n\,q_b)$ with largest-remainder rounding, where
$n$ is the number of assigned slots and $q_b$ is the exploration knob's
band share, so every band receives slots at every setting
([`docs/DESIGN.md` §6](docs/DESIGN.md#6-the-two-knobs-size-and-exploration)).

## Development

```bash
uv sync                          # create the environment from uv.lock
uv run pytest                    # tests
uv run ruff check . && uv run ty check
uv run pre-commit install        # ruff, ruff-format, detect-secrets, ty on commit
```
