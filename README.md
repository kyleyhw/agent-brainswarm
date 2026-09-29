# agent-brainswarm

A multi-agent idea generation and ranking system built as a Claude Code
skill. Written with the goal of producing diverse, rigorously critiqued
ideas that can be handed to [agent-evolve](https://github.com/kyleyhw/agent-evolve)
for testing and improvement.

Like agent-evolve, this is a skills bundle installed once and used across
projects. You drive it by talking to Claude:

```
brainswarm trading strategies that trade on many days and optimise growth and diversification
brainswarm ways to cut our CI time — quick, surprise me
/brainswarm path/to/brainswarm.yaml
```

**brainswarm the ideas, evolve the code.** A run sends a swarm of
independent agents to research and propose ideas, has other agents attack
every idea with justified criticism, develops the most promising and the
most unusual ones, and ranks the result with honest uncertainty. You get
every idea with its full critique record, the top idea families, labelled
wildcards, and export bundles for agent-evolve. Nothing is deleted:
weak ideas are ranked low, not hidden.

## Install

In any Claude Code session (local or on the web), say:

```
install brainswarm from https://github.com/kyleyhw/agent-brainswarm
```

Claude clones the repository and runs its installer. By hand, that is:

```bash
git clone https://github.com/kyleyhw/agent-brainswarm ~/agent-brainswarm
cd ~/agent-brainswarm && uv run python install.py   # CLI as a uv tool; skill + 9 role agents into ~/.claude/
```

Then say "brainswarm …". The skill never triggers on "brainstorm". The skill
is usable at once; role agents installed mid-session can take a few minutes
to appear, and the skill writes the rubric meanwhile. A cloud container is
discarded when the session ends, so each new cloud session needs the one-line
install again.

The role files live in `agents/` rather than `.claude/agents/` on purpose:
Claude Code runs a project-level agent's guard hook only after workspace
trust, which cloud sessions never grant, so only the installed user-level
links are guaranteed to be guarded.

## Documentation

| Document | Content |
|---|---|
| [`docs/DESIGN.md`](docs/DESIGN.md) | Design specification: purpose, pipeline, knobs, fixation controls, scoring and its derivation, privacy, security, architecture, logging, watch list, design review, references |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | Benchmark protocol: brainswarm versus a single strong agent, blinded human rating |
| [`docs/studies/uncertainty_coverage.py`](docs/studies/uncertainty_coverage.py) | Coverage study behind the choice of uncertainty method |
| [`docs/studies/token_calibration.py`](docs/studies/token_calibration.py) | Token calibration: dispatch counts per preset times measured per-dispatch costs |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Development phases and task status |
| [`examples/README.md`](examples/README.md) | Live and offline demos; controlled reruns of the demo with the fixes |
| [`tests/reports/`](tests/reports/) | Dated test reports |

## Directory structure

```
agent-brainswarm/
├── .claude/skills/brainswarm/SKILL.md  # /brainswarm: the referee, a thin loop over next/ingest
├── agents/brainswarm-*.md           # 9 roles with tool allowlists and the guard hook, linked
│                                    #   into ~/.claude/agents by install.py: ideator, generator,
│                                    #   clusterer, critic, checker, advocate, workshop, judge,
│                                    #   rubric-auditor
├── src/agent_brainswarm/
│   ├── pipeline.py                  # the state machine (plan / check / finish per phase)
│   ├── scoring.py                   # Bradley–Terry / Plackett–Luce, Laplace, bootstrap
│   ├── schedule.py  assign.py       # critic and finals designs; slot banding
│   ├── critique.py  select.py       # critique checks; gates, slots, top families
│   ├── report.py  records.py        # digest, report.md, report.html
│   ├── library.py  usage.py         # idea library; token accounting
│   ├── export.py  sandbox.py        # agent-evolve bundles; Docker runner
│   └── guard.py  models.py  config.py  rubric.py  state.py  cli.py
├── docs/  DESIGN.md  BENCHMARK.md  studies/  figures/
├── examples/                        # demos/ (3 manifests), recorded demo run, offline replay,
│                                    #   demo-reruns/ + rerun_comparison.py (controlled reruns)
├── benchmark/                       # single-agent baselines, blinded judging packs
├── tests/                           # unit + end-to-end tests with fake agents; reports/
├── install.py  PROJECT_PLAN.md  CLAUDE.md
└── pyproject.toml  uv.lock  .pre-commit-config.yaml  .secrets.baseline
```

## Main logic

The session running `/brainswarm` is a **referee**: it frames the brief and
the rubric, then loops over two commands and launches the subagents they
name. It never contributes an idea or a verdict.

```
brainswarm next <run>    ->  referee action, or a list of dispatches (role, model, prompt)
(subagents read their task file, write JSON to their output file, reply one line)
brainswarm ingest <run>  ->  validate; one retry for invalid output; advance
```

```
rubric -> audit -> freeze -> angle round -> clusters -> ideate (no web) -> research
  -> clusters -> critique -> checker -> advocate -> workshop -> re-critique
  -> [fact-check] -> finals -> boundary -> report
```

- **Blind generation.** Generators propose angles and far domains blind;
  code bands them by popularity and assigns slots across common, middle
  and rare bands. Generators sketch ideas with no web access first (a
  pre-registration), then research them. Generation never sees other
  ideas or earlier runs.
- **Justified critique.** Every criticism quotes the card, gives a
  mechanism, evidence, severity and falsifier. Code checks the quote;
  generic and templated critiques are flagged and carry no weight.
- **Workshop.** Top-value, wildcard and advocate-promoted ideas are
  developed by a different model, which answers every serious critique.
  Fresh critics then judge whether the answers hold.
- **Finals.** An incomplete round robin. Each pair goes to one judge
  model, which sees it in both presentation orders in two different
  dispatches; this is what separates the judges' position bias from their
  disagreement (the demo's judges preferred the first-listed idea 20 times
  in 24).

Two knobs: **size** (`quick` / `standard` / `deep`: ~4–6M / ~10–15M / ~16–23M new
tokens) and **exploration** (`conservative` / `balanced` / `wild`: where
effort goes, at the same cost). Neither changes how ideas are judged.

### Scoring model

Finals verdicts use the Bradley–Terry model with a position-bias parameter
$\gamma$:

$$
P(\text{first} \succ \text{second}) = \sigma(\beta_\text{first} - \beta_\text{second} + \gamma),
\qquad \sigma(x) = \frac{1}{1+e^{-x}}.
$$

Critics' top-3 rankings use Plackett–Luce, which reduces to the same model
for two items. With the prior $\beta_i, \gamma \sim \mathcal N(0, \tau^2)$
($\tau = 1.5$), the log-posterior is strictly concave, so Newton's method
finds the unique maximum, and $\sum_i \beta_i = 0$ holds automatically at
it. Finalists and non-finalists are fitted separately and never put on one
scale. Uncertainty comes from the Laplace approximation (below 30 dispatch
clusters) or a dispatch-level bootstrap. A coverage study showed the
bootstrap under-covers with ~20 clusters (90 % for a nominal 95 %) while
Laplace holds ≥ 97.9 %. Reported per idea: rank with its 95 % interval,
$P(\text{top-}k)$, tier, and mean win probability against the field.
Derivations are in [`docs/DESIGN.md` §10](docs/DESIGN.md#10-scoring).

## Demo

- **Offline, zero tokens:** `uv run python examples/demo_run.py` replays a
  recorded live run through the real code and checks that the ranking is
  reproduced exactly.
- **Live, ~1.4M new tokens each:** in Claude Code, say "run the brainswarm
  demo" or `brainswarm init --manifest examples/demos/<name>.yaml`. Three
  concrete briefs with stated constraints:
  - `etf-strategy.yaml`: a rule-based ETF trading strategy (recorded run);
  - `exoplanet-transit.yaml`: a low-cost transit-photometry setup for a
    20 cm amateur telescope;
  - `home-heating.yaml`: cutting a house's heating energy by 30 % for
    under $3,000.

See [`examples/README.md`](examples/README.md) for the recorded results and the reruns.

## Development

```bash
uv sync
uv run pytest                        # 69 tests incl. end-to-end runs with fake agents
uv run ruff check . && uv run ty check
uv run pre-commit install            # ruff, ruff-format, secret scanning, ty on commit
```
