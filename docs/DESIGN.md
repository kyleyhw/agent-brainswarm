# brainswarm — design

> **Status: design phase (2026-09-28).** This document is the source of truth
> for what brainswarm is and how it will work. Nothing in the protocol is
> implemented yet; the repo contains a scaffold only. Work is tracked in
> [`PROJECT_PLAN.md`](../PROJECT_PLAN.md); the repository overview is in the
> [README](../README.md). Where a decision is still open it says so explicitly
> in [§20](#20-open-questions).

## Contents

1. [Purpose](#1-purpose)
2. [Relationship to agent-evolve](#2-relationship-to-agent-evolve)
3. [Invocation and interaction](#3-invocation-and-interaction)
4. [Prime directives](#4-prime-directives)
5. [Pipeline](#5-pipeline)
6. [The two knobs: size and exploration](#6-the-two-knobs-size-and-exploration)
7. [Design fixation controls](#7-design-fixation-controls)
8. [Repeat runs and the idea library](#8-repeat-runs-and-the-idea-library)
9. [Outputs and export](#9-outputs-and-export)
10. [Scoring](#10-scoring)
11. [Storage and privacy](#11-storage-and-privacy)
12. [Security](#12-security)
13. [Architecture](#13-architecture)
14. [Logging and telemetry](#14-logging-and-telemetry)
15. [Watch list: known weak points](#15-watch-list-known-weak-points)
16. [Gaps to verify before building](#16-gaps-to-verify-before-building)
17. [Demo](#17-demo)
18. [Build order](#18-build-order)
19. [Design history: what we took from prior art](#19-design-history-what-we-took-from-prior-art)
20. [Open questions](#20-open-questions)
21. [References](#references)

---

## 1. Purpose

**brainswarm generates ideas at scale and ranks them honestly.** Given a
brief with guidelines ("come up with a strategy for trading stocks; it
should trade on many days and optimise for growth and diversification",
"think of ways to improve ___", "think of ways to solve ___"), it runs a
swarm of independent agents that research and propose ideas, has other
agents critique every idea with justified criticism, develops the most
promising and the most unusual ideas further, and ranks the results with
honest uncertainty.

**Output:** a ranked list of *every* idea with its full critique record, a
shortlist of the **top few idea families** (default 5, each with its closest
variants), labelled wildcards, and optional export bundles for follow-up work
(for example with agent-evolve).

**It is deliberately not:**

- a consensus or decision tool (it ranks many options; it does not converge
  on one answer),
- a literature survey,
- a code optimiser (that is agent-evolve),
- an actor: it never trades, edits code outside its own run folder, or
  publishes anything.

**Use-case shapes it must handle** (kept flexible, not hard-coded):

| Shape | Input | Downstream measurable? | Outside knowledge |
|---|---|---|---|
| Strategy design | a brief | often (e.g. a backtest) | some |
| Improve ___ | an artifact (repo, system, paper, process) | sometimes | mostly the artifact |
| Solve ___ | a problem statement | usually not | often |

Where a downstream measurement exists, brainswarm's ranking is a *"worth
testing"* prior, never a claim that the idea works.

## 2. Relationship to agent-evolve

**Independent tool, shared philosophy, compatible output** [[14]](#ref-agent-evolve). brainswarm does
the *coming up with ideas* part that agent-evolve is not designed for;
agent-evolve is good at testing and improving an idea once it is code.
Pairing: **brainswarm the ideas, evolve the code.**

- brainswarm never imports, calls, or requires agent-evolve.
- The only link is `brainswarm export`, which writes files (a draft
  `agent-evolve.yaml`, `hypotheses.md`, an implementation brief). That file
  set is the entire contract. If the `agent-evolve` CLI happens to be on
  PATH, export runs its `validate` as a courtesy; otherwise it skips with a
  note.
- Shared pieces (sandbox runner, usage parser, report styling) are **copied,
  not imported**. Extract a shared library only if a third tool appears.

Philosophy carried over from agent-evolve:

| agent-evolve | brainswarm |
|---|---|
| Hypothesis pre-registration | Rubric frozen and hashed before dispatch; raw ideas saved before research |
| "Never re-run an eval to shop for a better number" | "Never re-judge to shop for a verdict"; every judgment recorded |
| Negative-result ledger | Graveyard with reasons; known-false claims ledger |
| Adversarial reviewer ("if unsure, REJECT") | Harsh, stake-free critics whose critiques must be justified |
| mutate / crossover / explore operators | Workshop (mutate, graft from siblings) and explore-lens generators |
| Pareto front | Secondary quality × novelty view |
| No winner is a valid outcome | "Not separable" tiers are a valid outcome |
| Prompt rules also enforced in code | Same: blinding, swaps, rubric freeze, critique checks, scoring in code |

Notes from reading agent-evolve (none require changing agent-evolve):

- agent-evolve has **no manifest field for seed hypotheses**. Export works
  around this: reference `hypotheses.md` in the evolve prompt. An optional
  `seed_hypotheses:` field in agent-evolve would be a convenience, not a
  requirement.
- **Idea → code gap.** agent-evolve needs a runnable baseline; a brainswarm
  idea is text. Each export includes an implementation brief; the first
  working version is an ordinary coding step before evolve.
- agent-evolve's **sibling mode** (catalogues of strategy classes) fits
  "separate evolves on each of the top few ideas".
- In agent-evolve, metric inference is done by the *session* following
  SKILL.md (Phase 0, Path B); the Python package validates, parses, and
  applies. brainswarm keeps that split and tightens it (§5, Phase 0).

## 3. Invocation and interaction

- **Command:** `/brainswarm`, or say **"brainswarm …"** in prose, exactly
  like `/evolve` / "evolve …".
  - `brainswarm trading strategies that trade on many days and optimise growth and diversification`
  - `brainswarm ways to cut our CI time — quick, surprise me`
  - `/brainswarm path/to/brainswarm.yaml`
- **Deliberately distinctive trigger.** A standard run costs millions of
  tokens; the skill must **not** trigger on "brainstorm", "mull it over", or
  casual requests for a few ideas. The skill description says so
  explicitly.
- **Autonomous by default.** No questions unless the brief is unrunnable.
  Every assumption is written to an "Assumptions I made about your brief"
  log shown in the preflight card and the report.
- **Opt-in human checkpoint** after clustering (prune or steer before
  critique). Off by default.

**How the human receives information:**

1. **Preflight card** (chat): brief as interpreted, inferred rubric,
   assumptions, setting + exploration, token estimate. Shown, not asked;
   the user can interrupt.
2. **Progress**: one line per phase (`critique 14/20 · 3.1M tokens`), no
   agent chatter.
3. **Notification** on completion where the environment supports it.
4. **Digest** (chat, ~15 lines): top families as one-liners, wildcards,
   what changed vs last run, tokens used, a Limitations line only if
   something degraded, path to the report.
5. **Follow-up questions** in the same conversation, answered from the run's
   structured data ("why did 7 lose to 3?", "show every fatal critique of the
   options idea"). Pull, not push.
6. **Report files** in the run folder: `report.md` and a self-contained
   `report.html`. Publishing a hosted page is offered, never automatic.

## 4. Prime directives

Draft; will be carried into `SKILL.md` verbatim.

1. **The referee never contributes.** The session running `/brainswarm`
   never generates, critiques, workshops, or judges ideas.
2. **The rubric is frozen before dispatch.** Code refuses to judge if the
   rubric hash has changed.
3. **Generation is blind.** No generator sees another generator's ideas or
   the idea library.
4. **Rank, don't remove.** No idea is deleted. Only constraints the user
   stated (plus the default legality/ethics gate) can bar an idea from the
   shortlist, and barred ideas stay visible with the reason. Some stupid
   ideas are an acceptable price for not over-filtering.
5. **Every criticism is justified or carries no weight.**
6. **Never re-judge to shop for a verdict.** Every judgment is recorded.
7. **Numbers come from code.** Token counts, scores, and intervals are
   computed, never reported by a model.
8. **brainswarm recommends; it never acts.**
9. **Stop at the report.**

## 5. Pipeline

```
0 Frame ─ 1 Angle & domain round ─ 2 Generate ─ 3 Cluster ─ [checkpoint, opt-in]
  ─ 4 Critique ─ 5 Workshop + re-critique ─ 6 Finals ─ 7 Aggregate & report ─ stop
```

Agents run in waves of ~10. Every phase checkpoints to disk; the referee
reads only code-built digests (never raw cards or critiques) so its context
survives a long run, and `brainswarm resume <run>` continues after a crash
or compaction.

### Phase 0 — Frame (referee + one audit subagent + code)

- Parse the brief or load `brainswarm.yaml`.
- **Infer the rubric** from the guidelines (agent-evolve Path B style):
  - `gate` criteria: **only constraints the user stated**, plus the default
    gate *illegal or clearly unethical*. Gate failures are classed
    **fatal** or **fixable**; fixable ones go to the workshop, not the bin.
  - `judged` criteria: inferred from the guidelines (e.g. "growth",
    "diversification"), each with a written definition and anchors, plus a
    fixed core: value/usefulness, feasibility, specificity, fit to brief,
    novelty, upside-if-it-works, probability-it-works.
  - `measured` criteria: optional, a command that emits a number (e.g. a
    sandboxed sanity backtest), labelled *sanity check, not evidence*.
- **Audit**: a separate subagent checks the draft rubric against the brief
  for missing criteria, criteria that reward the wrong thing, and criteria
  biased toward one idea type.
- **Freeze**: code writes `rubric.yaml`, hashes it, and records the hash.
- **Preflight card** is shown; the run continues unless interrupted (or
  pauses here if the checkpoint is opted in).

### Phase 1 — Angle and domain round (blind, cheap)

- Every generator privately proposes **3 angles** (how to approach the
  problem) and **3 domains far from the problem** to borrow mechanisms
  from ("not the first ones that come to mind"). Angles and domains only,
  no ideas.
- Code clusters the pools and measures **popularity** (how many generators
  proposed each cluster), giving **common / middle / rare** bands. Domains
  are also banded by distance: **near / mid / far**.
- The referee writes **no** lenses; the pool is the union of ~20 minds.

### Phase 2 — Generate

- **Slot types** (mix set by the exploration knob, §6):
  - **assigned angle** — an angle from the pool, preferably one proposed by
    a *different* generator, sampled across bands;
  - **free** — the generator chooses its own direction;
  - **cross-domain** — a domain from the pool (proposed by another
    generator, sampled across distance bands; code may skip domains used in
    previous runs). **No declining:** the generator must produce an idea
    through that domain and records a transfer rating
    (`strong` / `partial` / `stretch`). Nonsense ideas simply rank low.
- **Ideate before searching.** Step 1: write raw ideas without web access;
  code timestamps and saves them (pre-registration). Step 2: research
  (web + sandbox) to develop and check them. New ideas found while
  researching are allowed and tagged `research-derived`.
- **3 ideas per generator**, each as an **idea card**:
  title, one-line pitch, mechanism, why it might work (with sources),
  key assumptions, how it fails, cheapest test, effort, optional operational
  spec (precise enough to implement/backtest), provenance (slot type,
  angle/domain, band, transfer rating, pre-search vs research-derived).
  Word caps enforced by code.
- **Framing: competitive.** "Your ideas will face hostile critics and be
  ranked against ~60 others."
- **Tools:** web search/fetch (runaway ceiling ~40 calls, a safety stop, not
  a cost saving), sandboxed code (§12). History-blind (§7).

### Phase 3 — Cluster

- Merge only **near-duplicates**; keep variants as siblings; err toward
  splitting; list every merge in the report.
- Compare against the **idea library** (§8): tag each idea `new`,
  `variant`, or `repeat`.
- **Rediscovery**: count how many generators (and how many *model
  families*) independently found each idea.
- Record the **yield curve**: unique clusters as each generator is added.

### Phase 4 — Critique

- Each idea is reviewed by **~6 critics** (never its author; preferably a
  different model). Critics receive anonymised cards.
- **Framing: harsh and stake-free.** "Steelman it, then try to kill it."
  Critics are reviewers, not competitors, so they have no reason to sink
  rivals.
- **Targeted web lookups only** (~5): to check the specific claims and
  citations in the card under review, not to research the topic.
- **Justified-critique schema** (code rejects items missing a field):

  | Field | Rule |
  |---|---|
  | `target` | a quote from the card; code fuzzy-matches it |
  | `mechanism` | why it fails — the causal story |
  | `evidence` | citation, calculation, counter-example, or brief reference |
  | `severity` | `fatal` / `major` / `minor` |
  | `falsifier` | what would show this critique wrong, or what fix answers it |

- **"Unproven" is not an admissible criticism on its own**; the critic must
  name the mechanism that would fail.
- **Generic-critique filter** (down-weights, never deletes):
  - *substitution test*: would the critique still be true attached to a
    random other idea in the batch?
  - *repetition check*: the same critic making nearly the same point about
    3+ ideas.
- Critics score **upside-if-it-works** and **probability-it-works**
  separately, and rank their batch → input to the preliminary scores (§10).
- Critics receive the **known-false claims ledger** from earlier runs.

### Phase 5 — Workshop (default on) and re-critique

- **Slots** (standard = 12), split value / wildcard / deepen by the
  exploration knob (§6). On a first run there is no library, so deepen
  slots go to value.
  - *value*: top by preliminary value;
  - *wildcard*: most novel, most divisive (high critic disagreement), and
    high-upside/low-probability ideas;
  - *deepen*: ideas from the library worth pushing further (top ideas,
    earlier wildcards, ideas with open critiques).
- **Graveyard advocate**: one agent reviews the ideas that did not get a
  slot and may promote 1–2 it thinks were wrongly passed over.
- **Workshop agent** (a different model from the idea's author; web +
  sandbox) produces **idea v2**:
  1. a response to **every** major/fatal critique: *fixed* (idea changes),
     *rebutted* (with evidence), or *conceded* (known limitation);
  2. depth: concrete mechanism, parameters, step-by-step plan, assumptions
     with evidence, failure modes, **cheapest first experiment**, kill
     criterion;
  3. optional sandbox sanity check (labelled as such);
  4. grafts from sibling ideas, with provenance.
- **Drift guard**: if v2 is no longer the same idea it becomes a new idea,
  not a replacement.
- **Re-critique**: 2–3 fresh critics check whether the fixes hold and what
  new flaws appeared.
- `deep` runs a second workshop round.

### Phase 6 — Finals

- Workshopped ideas (+ **returning champions**: the library's top 3 on
  repeat runs) compete in **pairwise matches judged in both orders** by a
  mixed-model panel (3 judges standard, 5 deep). A win counts only if both
  orders agree; otherwise it is a tie.
- **Boundary focus**: extra comparisons around the top-k cutoff so #5 vs #6
  is resolved, not just #1.
- **Disputed critiques** (rebutted in the workshop) are ruled *upheld* or
  *overturned*, giving each critic a hit rate.
- **Fact-check**: web verification of the load-bearing claims of each
  finalist.
- Judges see anonymised, length-capped, identically structured cards.

### Phase 7 — Aggregate and report

- Fit scores (§10), build tiers, pick the **family-aware top-k**, attach
  variants, select wildcards, run bias checks, render the digest and
  report, write telemetry. **Stop.**

## 6. The two knobs: size and exploration

Two independent axes. Any combination is valid (`quick + wild` = cheap
long-shot sweep; `deep + conservative` = thorough practical search). Plain
language maps to both ("quick but surprise me").

**Neither knob changes how ideas are critiqued, judged, or ranked.** The
ranking is always "value, judged neutrally", so runs stay comparable.

### Size — how much work (and tokens)

| Setting | Shape | New tokens | Cache reads | Rough wall time |
|---|---|---|---|---|
| `quick` | 8 generators, critique, light finals, no workshop | ~2M | ~11M | ~30 min |
| `standard` (default) | 20 generators, targeted-web critique, 12 workshop slots, re-critique, full finals | ~8M | ~45M | ~1–2 h |
| `deep` | 30 generators, 2 workshop rounds, 16 slots, 5-judge finals | ~13M | ~80M | ~3 h+ |

Estimates are calibrated from measured subagent transcripts in the design
session (web-research subagents: ~50–120k new tokens and ~0.5–1.7M
cache-read tokens each). How subscription plans weight cache reads is not
published, so both numbers are reported. Wall times are guesses. Every run
logs actuals; the table is recalibrated from real runs. The preflight card
shows the estimate; the digest shows the actual.

### Exploration — where the work goes (same token cost)

| | conservative | balanced (default) | wild |
|---|---|---|---|
| Generator slots: angle / free / cross-domain | 70 / 25 / 5 % | 50 / 25 / 25 % | 30 / 20 / 50 % |
| Assigned-angle bands: common / middle / rare | 60 / 30 / 10 | 34 / 33 / 33 | 15 / 35 / 50 |
| Analogy distance: near / mid / far | 60 / 30 / 10 | 34 / 33 / 33 | 15 / 35 / 50 |
| Workshop slots (standard): value / wildcard / deepen | 8 / 2 / 2 | 5 / 4 / 3 | 3 / 7 / 2 |
| Wildcards shown with the top 5 | 0–1 | 2 | 4 |

No band is ever zero: common angles may be common because they are good;
rare ones are where surprises come from. Free slots already lean common, and
the assignment accounts for that. The mix is a hypothesis; per-band results
are logged so defaults can be moved on evidence. v1 is deterministic (no
auto-tuning) so runs stay comparable. Near/far analogy research reports
mixed effects of analogical distance on design output
[[9]](#ref-fu-2013), which is why every distance band is sampled and
measured rather than one being chosen a priori.

### Banding and allocation

Let the angle pool be partitioned into clusters $k = 1, \dots, K$, and let
$s_k$ be the number of distinct generators that proposed an angle in
cluster $k$ (its popularity). Clusters are assigned to the bands common,
middle and rare by the tertiles of $\{s_k\}$; ties at a tertile boundary go
to the more common band, so that a band is never populated by an arbitrary
split of equal-popularity clusters. Domains are banded the same way on a
distance rating (near, mid, far) given by the proposing generator.

Given $n$ assigned-angle slots and the knob's band shares $q_b$
($\sum_b q_b = 1$), band $b$ receives

$$
n_b = \lfloor n q_b \rfloor + \delta_b,
$$

where the $\delta_b \in \{0, 1\}$ distribute the remaining
$n - \sum_b \lfloor n q_b \rfloor$ slots to the bands with the largest
fractional parts $n q_b - \lfloor n q_b \rfloor$ (largest-remainder
rounding). This keeps $\sum_b n_b = n$ exactly and each $n_b$ within one
slot of its target $n q_b$. Within a band, clusters are drawn uniformly
without replacement (so one popular cluster cannot absorb a band's slots),
an angle is drawn within each cluster, and angles proposed by the receiving
generator are excluded where an alternative exists. All draws use a
recorded seed.

### Parameter provenance

Every fixed default below is provisional: chosen by judgment during design,
not fitted, and scheduled for recalibration from logged runs (§14).

| Parameter | Default | Basis |
|---|---|---|
| Generators (quick / standard / deep) | 8 / 20 / 30 | Standard is the owner's proposed swarm size (~20 agents); quick and deep scale it down and up. Diminishing returns are expected past a few dozen; the logged yield curve (§14) will locate the real knee. |
| Ideas per generator | 3 | Breadth over depth at generation; depth comes from the workshop. Three gives ~60 ideas at standard size, enough for a stable ranking without swamping critique. |
| Angles and domains proposed per generator | 3 + 3 | Yields ~60 of each at standard size: roughly three candidates per generator slot, so assignment can prefer angles from other generators. |
| Critics per idea | ~6 | Enough independent judgments per idea for the Plackett–Luce fit and for "raised by m of 6" counts to be meaningful, at ~20 critic agents in total. |
| Targeted lookups per critic | ~5 | Enough to check a card's load-bearing citations, not enough to research the topic (research belongs to generators). |
| Web-call ceiling per generator | ~40 | A runaway stop, set well above the 10–24 tool calls observed for research subagents in the design session. |
| Workshop slots (quick / standard / deep) | 0 / 12 / 16 | Standard develops ~20 % of ~60 ideas; the split is set by the exploration knob. |
| Re-critique critics | 2–3 | Checks fixes without repeating the full critique cost. |
| Finals judges (standard / deep) | 3 / 5 | Odd counts avoid split panels; two model families at minimum. |
| Top families shown | 5 | The owner's stated use: several ideas to take forward, not one. |
| Returning champions | 3 | Enough to benchmark against the previous best without crowding the finals. |
| Agent wave size | ~10 | Keeps concurrent subagents within observed practical limits; to be confirmed (§16.6). |
| Bootstrap resamples $B$ | 1000 | Standard choice for 95 % percentile intervals [[5]](#ref-efron-tibshirani-1993). |
| Band shares $q_b$ | §6 table | Hypotheses about the exploration–exploitation balance; every band non-zero by construction. |

### Overrides

Anything finer (e.g. `generators: 12`) is an advanced override in
`brainswarm.yaml`, like agent-evolve's manifest.

## 7. Design fixation controls

Fixation (anchoring on examples) is treated as a primary risk. Human design
research found people fixate on example features even when told to avoid
them [[8]](#ref-jansson-smith-1991), so "avoid these" instructions are not
relied on.

- **Blind generation, informed selection.** History (the library, earlier
  runs) enters only *after* generation: in clustering, novelty scoring,
  critique, workshop deepen slots, and returning champions.
- **The referee writes no lenses**; angles and domains are crowdsourced
  blind from the generators (Phase 1).
- **Ideate before searching** so web research develops ideas rather than
  seeding everyone from the same top search results; the pre-search vs
  research-derived tag measures how much research homogenises.
- **Known-false ledger goes to critics and workshop, not generators.**
- **Optional gap-fill wave** (opt-in, off by default): after clustering, a
  small labelled wave aimed at uncovered territory.
- **Model mix** for generators (Opus / Sonnet / Fable by default; external
  CLIs later).

Measured every run: repeat rate across runs, clusters per idea, angle-pool
diversity, pre-search vs research-derived similarity.

## 8. Repeat runs and the idea library

- Every run adds cards, clusters, scores, critiques, and refuted claims to a
  per-project **idea library** in `~/.agent-brainswarm/projects/<project>/`,
  tagged by topic, with **lineage** (run 3 idea 12 ← run 1 idea 4).
- New runs attach to the library automatically by topic.
  `--fresh-library` ignores history; `--continue <run>` weights the workshop
  toward deepening that run.
- **Duplicates are labelled, not deleted**: `new` / `variant` / `repeat`
  ("seen in run 2, ranked #14"). Novelty is scored against the whole
  library; repeats do not take workshop slots unless they add something new
  (mechanism, evidence, or an answer to an old critique).
- **Rediscovery is reported, not over-read**: "found 4× by 3 model
  families". Convergence may mean robustness or may mean a shared prior;
  cross-family rediscovery counts for more.
- **Returning champions**: the library's top 3 are re-judged in the new
  run's finals, so each run shows whether it beat the previous best.
  Scores are not merged across runs (different briefs, rubrics, judges).
- Deepening an existing idea is valued, not penalised: the rubric scores
  **value added**, and the main ranking is by value, not novelty.

## 9. Outputs and export

**Principle: rank, don't remove; label, don't hide.**

Report layers:

- **Top families** (default k = 5): distinct ideas from different clusters,
  each with its closest variants attached. Ties at the cutoff are included.
- **Wildcards** (count set by exploration knob), clearly labelled.
- **Full ranked list of all ideas**: tier/rank range, pitch, value,
  novelty, critique counts by severity, tags (`new` / `variant` / `repeat`
  / `rediscovered` / `research-derived` / slot type), workshop status.
- **Idea detail**: card (v1 → v2 diff), **every** critique grouped by
  severity with near-duplicates merged and counted ("raised by 4 of 6
  critics"), each with status (*fixed / rebutted / conceded / open*,
  *upheld / overturned*), evidence links, lineage, finals verdicts.
- **Graveyard**: ideas with no slot and why.
- **Run internals**: frozen rubric, assumptions, angle/domain pools and band
  yields, cluster map, bias and fixation metrics, generic-critique rate,
  critic hit rates, per-phase tokens, raw JSON.

Plain language throughout ("win chance vs an average idea", not
"Bradley–Terry strength"); uncertainty as bars and tiers, not bare numbers.

**Export** (`brainswarm export`):

| Command | Writes |
|---|---|
| `brainswarm export --top 5` | one folder per family, for separate evolves |
| `brainswarm export --family <idea>` | one folder: idea + its family, for one evolve with variants as mutation material |

Each folder: developed idea card, `hypotheses.md` (variants + open critiques
turned into tests, e.g. "does it survive transaction costs?"), metric
suggestions from the rubric's measurable criteria, implementation brief,
draft `agent-evolve.yaml` with placeholders.

## 10. Scoring

- **Model**: Bradley–Terry over all pairwise outcomes
  [[1]](#ref-bradley-terry-1952) (Plackett–Luce
  [[2]](#ref-luce-1959)[[3]](#ref-plackett-1975) for critics' batch
  rankings), fitted **once** after all judgments are in (not online Elo,
  which is order-dependent on static data; Chatbot Arena moved to
  Bradley–Terry for the same reason [[6]](#ref-chiang-2024)).
- **Scale shown to humans**: "chance of beating an average idea in this
  run" (0–100 %), converted from the log-odds strength.
- **Uncertainty**: bootstrap [[4]](#ref-efron-1979) (1000 resamples)
  **clustered by judge** [[7]](#ref-field-welsh-2007) (one judge's calls
  are correlated); report **rank ranges** ("#3, 95 % CI #2–#6") and
  **tiers** of statistically tied ideas.

### Formulation

Each idea $i \in \{1, \dots, N\}$ has a positive worth $\pi_i$, with
$\beta_i = \log \pi_i$. The Bradley–Terry model states

$$
P(i \succ j) = \frac{\pi_i}{\pi_i + \pi_j}
            = \frac{1}{1 + e^{-(\beta_i - \beta_j)}}
            = \sigma(\beta_i - \beta_j).
$$

Only differences $\beta_i - \beta_j$ enter, so $\beta$ is identified up to
an additive constant; the constraint $\sum_i \beta_i = 0$ fixes it. With
$w_{ij}$ the number of matches $i$ won against $j$, the log-likelihood is

$$
\ell(\beta) = \sum_{i \neq j} w_{ij} \log \sigma(\beta_i - \beta_j).
$$

A tie (the two presentation orders disagree, §5 Phase 6) contributes half a
win to each side, $w_{ij} \mathrel{+}= \tfrac12$ and
$w_{ji} \mathrel{+}= \tfrac12$. An idea that wins every match has no finite
maximum-likelihood estimate ($\beta_i \to \infty$), so the fit maximises the
penalised likelihood

$$
\ell_\lambda(\beta) = \ell(\beta) - \frac{\lambda}{2} \sum_i \beta_i^2,
$$

equivalent to a Gaussian prior $\beta_i \sim \mathcal N(0, 1/\lambda)$;
$\lambda$ is set small enough that it only matters for undefeated or
winless ideas (value to be fixed during implementation and documented).

A critic's ranking $\rho = (\rho_1, \dots, \rho_K)$ of a batch of $K$ ideas
enters through the Plackett–Luce likelihood, which treats the ranking as
successive choices of the best remaining idea:

$$
P(\rho) = \prod_{k=1}^{K} \frac{\pi_{\rho_k}}{\sum_{m=k}^{K} \pi_{\rho_m}}.
$$

For $K = 2$ this reduces to the Bradley–Terry probability, so both kinds of
evidence share one set of worths.

The reported score is $p_i = \sigma(\beta_i - \bar\beta) = \sigma(\beta_i)$
(since $\bar\beta = 0$): the probability of beating a hypothetical idea of
exactly average strength. It is not the mean of $i$'s pairwise win
probabilities; it is chosen because it is monotone in $\beta_i$ and
readable.

**Bootstrap.** Let $J$ be the set of judges (critics in the preliminary
fit; judge × panel seat in the finals). For $b = 1, \dots, B$: draw $|J|$
judges from $J$ with replacement, take all judgments of each drawn judge,
refit $\beta^{(b)}$, and record each idea's rank $r_i^{(b)}$. The 95 %
rank interval of idea $i$ is the 2.5th to 97.5th percentile of
$\{r_i^{(b)}\}$. Resampling whole judges rather than individual judgments
keeps each judge's internal correlation, which a naive resample would
destroy and thereby understate uncertainty.

**Tiers.** Sort ideas by point estimate. Tier 1 contains the top idea and
every idea whose rank interval overlaps the top idea's interval; tier 2
starts from the best remaining idea, and so on.

**Few-judge caveat.** The finals have only 3–5 judges, and a cluster
bootstrap with so few clusters gives unreliable intervals. The finals
bootstrap design is an open item (§16.11).
- **Axes**: the main ranking is **value**. Per-criterion fits (novelty,
  feasibility, upside, …) give additional axes and a secondary
  quality × novelty Pareto view.
- **Preliminary scores** (from critique) choose workshop value slots;
  **final scores** (from finals) produce the report ranking.
- **Stated limitation, in every report**: intervals measure judge *noise*,
  not judge *bias*. If every judge shares a blind spot the interval is
  narrow and wrong.

## 11. Storage and privacy

- Runs live in **`~/.agent-brainswarm/runs/<id>/`**, outside any repo, so
  they are never committed by accident. `--here` writes to
  `./brainswarm-state/` in the current project and adds it to `.gitignore`
  first.
- **Ephemeral environments** (cloud sessions): the home directory is
  reclaimed with the container. brainswarm warns at the end of such runs and
  offers a persistent location (a private repo, or `--here` in a private
  project).
- Nothing is published automatically. Sharing is explicit
  (`brainswarm report <id>`, or an offer to publish a private hosted page).
- **Private briefs**: search queries carry brief content to the web. A brief
  marked private runs with web off; brainswarm warns rather than pretending
  to split it.

## 12. Security

- **No agent acts on the world.** No trades, no broker APIs, no credentials,
  no writes outside the run folder.
- **Prompt injection via web pages**: blast radius is small by design
  (ideas only). Fetched content is data, never instructions; ideas resting
  on a single web source are flagged; critique exists to catch bad ideas.
- **Sandboxed code** (generators, workshop): container, **no network**, no
  `pip install` (pre-built image with common scientific packages; models
  sometimes invent package names that attackers register), CPU / memory /
  time limits, no environment secrets, writes to scratch only. Data an idea
  needs (e.g. price history) is fetched once into a **read-only cache**
  before agents run.
- **Tool allowlists per role** via agent definitions (§13); shell access
  for generators restricted to the sandbox wrapper. *Enforcement mechanism
  to be verified* (§16).
- **Scratch backtests are sanity checks, not evidence.** Held-out ranges are
  fixed by the referee; real performance claims belong to evolve.

## 13. Architecture

Same split as agent-evolve: **prose carries the protocol and its reasons;
code enforces what prose cannot.**

```
agent-brainswarm/
  .claude/skills/brainswarm/SKILL.md     # the one user-facing skill (referee)
  .claude/agents/brainswarm-*.md         # role prompts + tool allowlists
  src/agent_brainswarm/                  # the "hands"
  docs/DESIGN.md                         # this file
  examples/                              # demo brief, config, recorded run
  tests/
  install.py                             # (planned) symlink skill + agents into ~/.claude/
```

**Roles** (agent definitions; models are defaults, configurable):

| Role | Phase | Tools | Default model |
|---|---|---|---|
| generator | 1, 2 | web search/fetch, read, sandbox | mix of Opus / Sonnet / Fable |
| clusterer | 3 | none (reads staged files) | Sonnet |
| critic | 4, 5 | targeted web lookups, read | Sonnet (mixed where possible) |
| advocate | 5 | read | Sonnet |
| workshop | 5 | web search/fetch, read, sandbox | a model different from the author |
| judge | 6 | read (fact-checker variant: web) | Opus + Fable panel |
| rubric auditor | 0 | read | Sonnet |

Roles are **agent definitions** rather than skills because agent
definitions can carry tool allowlists. All dispatch happens from the
referee (subagents cannot spawn subagents).

**Python package `agent_brainswarm`** (planned modules; currently stubs):

| Module | Responsibility |
|---|---|
| `models` | frozen dataclasses: brief, rubric, idea card, critique, judgment, run config |
| `config` | presets (size × exploration), `brainswarm.yaml` overrides, validation |
| `rubric` | rubric freeze and hash check |
| `assign` | angle/domain banding and stratified slot assignment |
| `critique` | schema validation, quote matching, generic-critique filter |
| `library` | idea library, lineage, new/variant/repeat tagging |
| `scoring` | Bradley–Terry / Plackett–Luce, clustered bootstrap, tiers |
| `select` | family-aware top-k, wildcard and workshop slot selection |
| `sandbox` | containerised code runner (pattern copied from agent-evolve) |
| `usage` | token accounting from transcripts |
| `state` | run folder, checkpoints, resume |
| `report` | digest, markdown, HTML |
| `export` | export bundles |
| `cli` | `brainswarm validate / report / export / resume / feedback` |

## 14. Logging and telemetry

Everything stays in the private run folder.

| Category | What | Improves |
|---|---|---|
| Versioning | brainswarm version, per-role prompt hashes, model per agent, setting, overrides, random seeds | attributing outcome changes to prompt/model changes; reproducibility |
| Agent telemetry | tokens (uncached input, cache writes, cache reads, output), turns, tool calls by type, wall time, retries, parse failures, timeouts | cost tuning, fragile roles |
| Idea provenance | generator, model, slot type, angle/domain + who proposed it, band, transfer rating, pre-search vs research-derived, sources, cluster, library match, lineage | which slot types / bands / models produce winners |
| Critique outcomes | every item, generic flag, resolution, ruling | critic hit rate by model; generic-filter calibration |
| Health metrics | everything in §15 | drift and bias over time |
| Yield curve | unique clusters vs generators added | the real optimum number of generators |
| Estimate vs actual | tokens, wall time | honest settings table |
| **Human feedback** | ideas starred / pursued / exported, and later outcomes ("backtested: failed") | **the only ground truth**; whether rankings mean anything |

Token accounting notes from the design session: the Agent tool's reported
token figure appeared to be *final context size*, not cumulative usage; and
`output_tokens` in transcripts looked undercounted. Usage is therefore
parsed from transcripts with message-id dedupe, and each field carries a
reliability note until verified.

## 15. Watch list: known weak points

| Weak point | Signal | Response |
|---|---|---|
| Cross-domain prompts produce nonsense | transfer ratings; rank of cross-domain ideas | accept some nonsense; shrink share if never useful |
| Domain/angle pools converge on clichés (ant colonies, jazz) | distinct clusters in the pools | stronger "not the first that comes to mind"; favour rare |
| Band mix is a hypothesis | per-band yield | move defaults on evidence |
| Web research homogenises ideas | pre-search vs research-derived similarity | diversify search starting points by angle |
| Rediscovery misread as robustness | rediscovery by model family | report families, not raw counts |
| Shared model priors | repeat rate across runs; cross-model agreement | external CLIs later |
| Rubric misinferred (autonomous) | rubric-audit disagreements; assumptions log | shown in preflight so the user can interrupt |
| Critics harsher on novel ideas | novelty–rank correlation | tighten the "unproven" rule |
| Generic filter miscalibrated | flag rate; random spot-checks | recalibrate substitution test |
| Judge position bias [[10]](#ref-zheng-2023) | order-swap disagreement rate | more judges / other models |
| Judge verbosity bias | length–rank correlation | length caps are enforced |
| Judge self-preference | win rate when judge and author share a model | mixed panels |
| Anonymity leaks via writing style | judge verdicts tracking author family beyond chance | stricter card structure |
| Workshop homogenises ideas | similarity across v2s | rotate workshop models; terser instructions |
| Workshop drift | drift flags | treat as new idea |
| Clustering over-merges | merge count; spot-checks | err toward splitting |
| Over-filtering | wildcard success rate in finals; graveyard promotions | more wildcard slots |
| Sandbox results over-trusted | — | always labelled sanity check |
| Prompt injection | single-source ideas; odd content | flag; never act |
| Library goes stale | ledger entry age | date everything; re-check old facts |
| False rigour of intervals | — | report states noise ≠ bias |
| Harmful/illegal ideas | legality gate hits | fatal gate; stays visible, never shortlisted |

## 16. Gaps to verify before building

1. **Per-role tool restriction in Claude Code**: confirm agent-definition
   tool allowlists are enforced for subagents, and find a reliable way to
   limit generator shell use to the sandbox wrapper (e.g. a hook).
2. **Referee context budget**: digest-only reading; checkpoint and resume.
3. **Ephemeral storage** in cloud sessions (§11).
4. **Trigger collisions**: `/brainswarm` must not fire on "brainstorm";
   must not collide with `/evolve` ("improve X"). Could be tested with the
   skills-arena SDK.
5. **Partial failures**: one retry on malformed output, then continue
   without that agent; report the count.
6. **Environment differences**: web search availability, concurrency
   limits, long local runs killed by laptop sleep. Preflight reports what
   degrades.
7. **Reproducibility**: seeds for all code-level randomness; model IDs and
   prompt hashes logged.
8. **Fixture mode**: canned agent outputs drive the Python layer end to end
   (tests and the offline demo) at zero token cost.
9. **Transcript token accounting**: confirm fields, dedupe, output-token
   reliability.
10. **Does brainswarm beat one strong agent?** Benchmark (§18) is the first
    milestone after the MVP.
11. **Finals bootstrap with few judges.** A judge-clustered bootstrap with
    3–5 clusters is unreliable [[7]](#ref-field-welsh-2007). Candidates:
    resample judgments within judge (stratified), or treat judge × match
    order as the cluster; to be decided with simulated data.

## 17. Demo

**Tier 1 — offline replay (0 tokens, deterministic):**
`python examples/demo_run.py` replays a recorded run through the real code:
rubric freeze, band assignment, critique checks rejecting a misquote and
flagging a generic critique, workshop v1 → v2 diff, scores with tiers,
top-families shortlist, digest, HTML report, export bundle. Doubles as an
integration test (agent-evolve's `examples/demo_run.py` pattern).

**Tier 2 — live mini run (~0.3M new tokens, ~1–2M cache reads, ~10–15
min):** "run the brainswarm demo" loads `examples/brainswarm-demo.yaml`
(overrides on `quick`): 4 generators × 2 ideas, 1 critique each, 2 workshop
slots, finals among the top 4, web off, mostly Sonnet. Its recorded output is
committed and used by tier 1.

Demo brief (open, §20): "ways to reduce flaky tests in a Python repo"
(leaning: critiques are easy to judge as justified vs generic) or "core
mechanics for a solo card game" (shows off cross-domain slots).

Not demoed (too expensive): web research, the multi-run library.

## 18. Build order

Phases, tasks and their status are tracked in
[`PROJECT_PLAN.md`](../PROJECT_PLAN.md). The ordering principle: verify the
platform assumptions that shape the prompts (§16.1, 16.4, 16.9) before
writing them; build the Python layer with fixture mode before any live run;
benchmark against a single strong agent before building repeat-run
features.

## 19. Design history: what we took from prior art

- **zhjai/agent-arena** [[11]](#ref-zhjai-agent-arena) (evidence-first multi-agent debate): kept
  independence before discussion, evidence over consensus, preserved dissent,
  "what would change your mind", honest limitations, on-disk packets and
  digest read-back. Changed: 13 modes → two knobs; prose-only → prose + code;
  orchestrator no longer participates or judges; rubric with scales and
  swaps. Different purpose: it adjudicates one question; brainswarm
  generates and ranks many ideas.
- **skillsarena.ai** [[12]](#ref-skills-arena) (skill discoverability benchmark): kept "observe, don't
  ask" and frozen scenario sets (for our benchmark). Dropped online Elo,
  winner-beats-all counting, arbitrary grade weights, and its optimiser.
- **oyi77 agent-arena-skill** [[13]](#ref-oyi77) (on-chain agent registry wrapper): dropped;
  kept only the note that reputation should come from verified outcomes
  (→ human-feedback logging).
- **Also relevant**: Chatbot Arena (Bradley–Terry + bootstrap over online
  Elo) [[6]](#ref-chiang-2024), LLM-as-judge bias literature (position,
  verbosity, self-preference) [[10]](#ref-zheng-2023), design-fixation
  research [[8]](#ref-jansson-smith-1991), near/far analogy research (mixed
  results, so every distance is sampled and measured) [[9]](#ref-fu-2013).

The name: "brainswarm" — a play on *brainstorm* (many minds, thought,
eureka) that is distinctive enough not to trigger by accident, and a verb
like *evolve*.

## 20. Open questions

- Demo brief: flaky tests (leaning) or solo card game.
- Tool-restriction mechanism for roles (§16.1).
- Default workshop/judge model assignments once measured.
- Whether to add an optional `seed_hypotheses` field to agent-evolve later.
- Finals bootstrap design with few judges (§16.11).
- Penalty strength $\lambda$ for the Bradley–Terry fit (§10).

## References

<span id="ref-bradley-terry-1952">[1]</span> Bradley, R. A., & Terry, M. E. (1952). *Rank analysis of incomplete block designs: I. The method of paired comparisons.* Biometrika, 39(3/4), 324–345. [Link](https://doi.org/10.2307/2334029)

<span id="ref-luce-1959">[2]</span> Luce, R. D. (1959). *Individual Choice Behavior: A Theoretical Analysis.* New York: Wiley.

<span id="ref-plackett-1975">[3]</span> Plackett, R. L. (1975). *The analysis of permutations.* Journal of the Royal Statistical Society, Series C (Applied Statistics), 24(2), 193–202. [Link](https://doi.org/10.2307/2346567)

<span id="ref-efron-1979">[4]</span> Efron, B. (1979). *Bootstrap methods: Another look at the jackknife.* The Annals of Statistics, 7(1), 1–26. [Link](https://doi.org/10.1214/aos/1176344552)

<span id="ref-efron-tibshirani-1993">[5]</span> Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap.* New York: Chapman & Hall.

<span id="ref-chiang-2024">[6]</span> Chiang, W.-L., et al. (2024). *Chatbot Arena: An open platform for evaluating LLMs by human preference.* Proceedings of the 41st International Conference on Machine Learning. [Link](https://arxiv.org/abs/2403.04132)

<span id="ref-field-welsh-2007">[7]</span> Field, C. A., & Welsh, A. H. (2007). *Bootstrapping clustered data.* Journal of the Royal Statistical Society, Series B, 69(3), 369–390. [Link](https://doi.org/10.1111/j.1467-9868.2007.00593.x)

<span id="ref-jansson-smith-1991">[8]</span> Jansson, D. G., & Smith, S. M. (1991). *Design fixation.* Design Studies, 12(1), 3–11. [Link](https://doi.org/10.1016/0142-694X(91)90003-F)

<span id="ref-fu-2013">[9]</span> Fu, K., Chan, J., Cagan, J., Kotovsky, K., Schunn, C., & Wood, K. (2013). *The meaning of "near" and "far": The impact of structuring design databases and the effect of distance of analogy on design output.* Journal of Mechanical Design, 135(2), 021007. [Link](https://doi.org/10.1115/1.4023158)

<span id="ref-zheng-2023">[10]</span> Zheng, L., et al. (2023). *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* Advances in Neural Information Processing Systems 36, Datasets and Benchmarks Track. [Link](https://arxiv.org/abs/2306.05685)

<span id="ref-zhjai-agent-arena">[11]</span> zhjai. *agent-arena: Evidence-first multi-agent debate for Claude Code × Codex* (v0.2.6). GitHub repository. [Link](https://github.com/zhjai/agent-arena)

<span id="ref-skills-arena">[12]</span> Ben Barouch, E. *skills-arena* (skillsarena.ai). GitHub repository. [Link](https://github.com/Eyalbenba/skills-arena)

<span id="ref-oyi77">[13]</span> oyi77. *agent-arena-skill*, in *1ai-skills*. GitHub repository. [Link](https://github.com/oyi77/1ai-skills)

<span id="ref-agent-evolve">[14]</span> Kyle. *agent-evolve: Evolutionary code search with cooperating language-model agents.* GitHub repository. [Link](https://github.com/kyleyhw/agent-evolve)
