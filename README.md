# agent-brainswarm

A Claude Code skill that sends a swarm of independent agents to generate ideas for a problem,
has other agents attack every idea with justified criticism, develops the most promising and
the most unusual ones, and ranks the result with honest uncertainty. Written with the goal of
finding ideas worth testing, which can then be handed to
[agent-evolve](https://github.com/kyleyhw/agent-evolve) to be built and measured.

**brainswarm the ideas, evolve the code.** You describe a problem in one sentence:

```
brainswarm a rule-based ETF strategy that trades most days, keeps turnover low and never loses more than 20 %
brainswarm ways to cut our CI time — quick, surprise me
brainswarm how to cut my house's heating energy by 30 % for under $3,000
```

and get back every idea with its full critique record, the top idea families, labelled
wildcards, and export bundles for agent-evolve. Nothing is deleted: weak ideas are ranked
low, not hidden.

## What a run looks like

Everything below comes from a real recorded run (`examples/demo-run/`). The brief asked for a
rule-based, long-only strategy over 10 ETFs that trades at least 3 days a week, keeps weekly
turnover under 20 %, and holds maximum drawdown under 20 %. It ran at a reduced size with web
research off.

![What each stage of the demo run produced](docs/figures/demo_pipeline.png)

*Each box is one stage, left to right, with what it produced. The rubric had 5 hard rules
taken from the brief and 7 judged criteria. Four generators each proposed approaches and
"far domains" (fields unrelated to finance to borrow from) without seeing each other's; the
code grouped them by how many generators thought of them and gave each generator one
assignment: a middle-popularity approach, a rare far domain, or a free choice. The 8 ideas were
sketched before any research, so later research could not pull them toward the obvious. 66
critiques followed, each quoting the idea it attacks. The 4 most promising or unusual ideas
were developed further and re-checked by fresh critics, then compared in pairs. All 8 ideas
are in the final report.*

### One idea's path

**Origin.** Idea I004 came from a rare "far domain" slot: *power-grid frequency regulation*.
Grid operators keep an "N-1 contingency reserve", enough spare capacity to survive losing the
largest generator. The idea carried this over: hold enough cash to survive a stressed
20-day loss of the largest asset-class cluster, and cut risk twice as fast as it is restored.

**Critique.** A critic quoted one line of the idea, *"Within cluster: inverse 63-day vol,
halved if close < 200-day SMA, renormalized"*, and showed with arithmetic that it cannot work:

> Renormalizing within the cluster cancels the halving whenever every asset in the cluster is
> below its 200-day SMA, which is exactly the bear-market state. […] Five equity ETFs all
> below their SMA each get 0.5·v_i, and the sum is renormalized to 1, so the weights equal
> the unfiltered inverse-vol weights.

Every critique has this shape: the quoted target, a mechanism, evidence, a severity, and what
would prove the critic wrong. Code checks that the quote is really in the idea.

**Fix.** A different model developed the idea and answered every serious critique. On this
one: *"Agreed: renormalisation cancelled the filter. Trend now halves weights without
renormalising, so freed weight goes to cash."* A fresh critic then checked the new version
and judged that the fix holds.

### The result

![Finalists' ranks with 95 % intervals](docs/figures/demo_ranking.png)

*Each row is a finalist; the dot is its rank (1 = best) and the line its 95 % interval. On
the right is its estimated chance of beating a randomly chosen other finalist. Every interval spans ranks 1 to 4, so
the report's verdict was that the four cannot be separated at this size, with weak evidence
for I008. That verdict is the point: brainswarm reports how sure it is rather than a single
winner. The run also showed that the judges favoured whichever idea was listed first; the
finals design was changed to measure and remove that bias ([details](docs/studies/position_bias.md)).*

A step-by-step tour of this run, with each stage's output, is in
[`examples/README.md`](examples/README.md).

## Use cases

| Use case | Example | What you get |
|---|---|---|
| Strategy design | `brainswarm a long-only ETF strategy that trades most days with drawdown under 20 %` | Rule sets with parameters, kill criteria, and the cheapest test for each |
| Improve something | `brainswarm ways to cut this repo's test time without losing coverage` | Ranked improvements, the top ones exported to agent-evolve with a measurable metric |
| Solve a problem | `brainswarm how to cut home heating energy by 30 % for under $3,000` | Plans checked against your stated limits, with their assumptions and failure modes |

## What makes it different

- **Many independent ideas.** Generators never see each other's ideas or earlier runs, so the
  swarm does not converge on the first obvious answer.
- **Unusual ideas get a fair chance.** Part of the effort goes to rare approaches and far
  domains, and the most unusual ideas get development slots of their own. The exploration
  setting (`conservative` / `balanced` / `wild`) moves that effort without changing how ideas
  are judged.
- **Criticism must be justified.** Critiques quote the idea and give a mechanism and evidence;
  vague, templated ones are flagged and carry no weight.
- **Nothing is deleted.** Every idea stays in the report with its critique record; ideas that
  break a hard rule you stated are marked, not hidden.
- **Honest ranking.** Pairwise finals with measured judge bias, 95 % rank intervals, and a
  plain statement when ideas cannot be separated.
- **Memory across runs.** A per-project idea library tags new ideas as new, variants or
  repeats, brings earlier winners back into the finals, and remembers claims found false.
- **Hand-off to agent-evolve.** Top ideas export as bundles with hypotheses, an implementation
  brief and a draft `agent-evolve.yaml`.

## When not to use it

- **It is expensive.** A run costs about 4–6M new tokens (`quick`), 10–15M (`standard`) or
  16–23M (`deep`); the reduced demo cost about 1.4M. For a handful of ideas, ask Claude
  directly.
- **It has not yet beaten a single agent.** On the ETF brief, six independent reviewers rated
  brainswarm's finalists no better than a single strong agent's own top three, at about 24
  times the cost ([benchmark](docs/BENCHMARK.md)). That is one brief at reduced size with web
  research off; broader tests are pending.
- **It ranks ideas, it does not prove them.** Scores are judged preference by language models;
  whether an idea works is for testing, which is what agent-evolve is for.

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

Then say "brainswarm …". The skill never triggers on "brainstorm". Role agents installed
mid-session can take a few minutes to appear; the skill writes the rubric meanwhile. A cloud
container is discarded when the session ends, so each new cloud session needs the one-line
install again. The role files live in `agents/` rather than `.claude/agents/` on purpose:
Claude Code runs a project-level agent's guard hook only after workspace trust, which cloud
sessions never grant, so only the installed user-level links are guaranteed to be guarded.

## Demos

- **Offline, zero tokens:** `uv run python examples/demo_run.py` replays the recorded run
  above through the real code and checks that the ranking is reproduced exactly.
- **Live:** say "run the brainswarm demo", or `brainswarm init --manifest
  examples/demos/<name>.yaml`. Three briefs are ready, at about 1.4M new tokens each with web
  research off:
  - `etf-strategy.yaml`: the recorded run above;
  - `home-heating.yaml`: cutting a house's heating energy by 30 % for under $3,000;
  - `exoplanet-transit.yaml`: a low-cost transit-photometry setup for a 20 cm amateur
    telescope.

## How it works

The session running `/brainswarm` is a **referee**: it frames the brief and the rubric, then
loops over two commands and launches the subagents they name. It never contributes an idea or
a verdict.

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

- **Blind generation.** Generators propose angles and far domains blind; code bands them by
  popularity and assigns slots across common, middle and rare bands. Generators sketch ideas
  with no web access first (a pre-registration), then research them.
- **Justified critique.** Code checks each critique's quote; a checker agent flags generic
  critiques with a substitution test (would the critique fit any other idea unchanged?).
- **Workshop.** Top-value, wildcard and advocate-promoted ideas are developed by a different
  model, which answers every serious critique; fresh critics judge whether the answers hold.
- **Finals.** An incomplete round robin. Each pair goes to one judge model, which sees it in
  both presentation orders in two different dispatches, so the judges' position bias can be
  separated from their disagreement.

Two knobs: **size** (`quick` / `standard` / `deep`) sets how much work is done and **exploration**
(`conservative` / `balanced` / `wild`) sets where it goes, at the same cost. Neither changes
how ideas are judged.

### Scoring model

Finals verdicts use the Bradley–Terry model with a position-bias parameter $\gamma$:

$$
P(\text{first} \succ \text{second}) = \sigma(\beta_\text{first} - \beta_\text{second} + \gamma),
\qquad \sigma(x) = \frac{1}{1+e^{-x}},
$$

where $\beta_i$ is idea $i$'s strength. Critics' top-3 rankings use Plackett–Luce, which
reduces to the same model for two items. With the prior $\beta_i, \gamma \sim \mathcal N(0,
\tau^2)$ ($\tau = 1.5$), the log-posterior is strictly concave, so Newton's method finds the
unique maximum, and $\sum_i \beta_i = 0$ holds automatically at it. Finalists and
non-finalists are fitted separately and never put on one scale. Uncertainty comes from the
Laplace approximation (below 30 dispatch clusters) or a dispatch-level bootstrap; a coverage
study showed the bootstrap under-covers with ~20 clusters (90 % for a nominal 95 %) while
Laplace holds ≥ 97.9 %. Reported per idea: rank with its 95 % interval, $P(\text{top-}k)$,
tier, and mean win probability against the field. Derivations are in
[`docs/DESIGN.md` §10](docs/DESIGN.md#10-scoring).

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
├── examples/                        # the recorded run and its tour, demo manifests, replay,
│                                    #   figures, controlled reruns
├── benchmark/                       # single-agent baselines, blinded packs, LLM reviewer panel
├── tests/                           # unit + end-to-end tests with fake agents; reports/
├── install.py  PROJECT_PLAN.md  CLAUDE.md
└── pyproject.toml  uv.lock  .pre-commit-config.yaml  .secrets.baseline
```

## Documentation

| Document | Content |
|---|---|
| [`examples/README.md`](examples/README.md) | Step-by-step tour of the recorded run; running the demos |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Design specification: purpose, pipeline, knobs, fixation controls, scoring and its derivation, privacy, security, architecture, logging, watch list, design review, references |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | Benchmark: brainswarm versus a single strong agent, with results |
| [`docs/studies/position_bias.md`](docs/studies/position_bias.md) | Judge position bias: controlled reruns of the demo and the crossover finals design |
| [`docs/studies/uncertainty_coverage.py`](docs/studies/uncertainty_coverage.py) | Coverage study behind the choice of uncertainty method |
| [`docs/studies/token_calibration.py`](docs/studies/token_calibration.py) | Token calibration: dispatch counts per preset times measured per-dispatch costs |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Development phases and task status |
| [`tests/reports/`](tests/reports/) | Dated test reports |

## Development

```bash
uv sync
uv run pytest                        # 70 tests incl. end-to-end runs with fake agents
uv run ruff check . && uv run ty check
uv run pre-commit install            # ruff, ruff-format, secret scanning, ty on commit
uv run python examples/make_figures.py   # redraw the README figures from the recorded run
```
