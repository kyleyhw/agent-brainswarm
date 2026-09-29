# Examples

| File | What it is |
|---|---|
| `demos/etf-strategy.yaml` | Manifest for the live mini demo: a rule-based ETF trading strategy (recorded below) |
| `demos/exoplanet-transit.yaml` | Manifest: a low-cost exoplanet-transit setup for a 20 cm amateur telescope (not yet run) |
| `demos/home-heating.yaml` | Manifest: cutting home heating energy by 30 % for under $3,000 (not yet run) |
| `demo-run/` | A recorded live run of that manifest: brief, config, rubric, every task file and agent output, the code-owned `data/`, and the rendered `report.md` / `report.html` |
| `demo_run.py` | Offline replay: re-runs the code layer over the recorded agent outputs (zero tokens) and checks the ranking is reproduced exactly |
| `demo-reruns/` | New agent outputs of three controlled reruns of the recorded run (finals-only, crossover, from-workshop) |
| `rerun_comparison.py` | Rebuilds the reruns offline from `demo-run/` plus `demo-reruns/` and writes `demo-reruns/comparison.json` and the figure below |

## Running the demos

```bash
uv run python examples/demo_run.py        # offline, zero tokens, ~5 s
```

Live (in Claude Code, after `uv run python install.py`): say "run the
brainswarm demo", or `brainswarm init --manifest examples/demos/<name>.yaml`
and follow `/brainswarm`. All three manifests use the same reduced `quick`
size as the recorded run (4 generators x 2 ideas, 2 critic reviews per
idea, 4 workshop slots, web off), so each should cost about 1.4M new
tokens. The two unrun briefs were chosen because their outcomes are
measurable against physics rather than taste: photometric scatter in
mmag per bin for the transit setup, and heat-loss arithmetic
($Q = UA\,\Delta T$ summed over heating degree-days) for the house. They
therefore test whether critics catch quantitative errors, which the
trading brief could not.

## The recorded run (2026-09-29)

**Brief.** A rule-based, long-only strategy for 10 liquid ETFs that trades
on at least 3 days a week, keeps weekly turnover at or below 20 %, uses
only daily closes, and optimises growth with maximum drawdown below 20 %
while staying diversified. Reduced `quick` size: 4 generators x 2 ideas,
2 critic reviews per idea, 4 workshop slots, full round-robin finals, web
off.

| Phase | Outcome |
|---|---|
| Rubric | 15 audit issues; clarifications accepted, scales/weights rejected (pairwise design); 5 user-stated gates + legality |
| Angle round | 8 angles, 8 far domains; slots: 2 angle (middle band), 1 cross-domain (rare), 1 free |
| Generation | 8 pre-registered sketches -> 8 cards; the cross-domain slot produced two power-grid ideas (droop control, N-1 contingency reserve) |
| Critique | 66 justified critiques; 3 failed the substitution test (generic); 3 malformed outputs retried |
| Workshop | 4 ideas developed by a different model; 3 over the 400-word cap were sent back once |
| Re-critique | 12 critiques of developed versions; no drift |
| Finals | 4 finalists, 12 ordered verdicts from a Sonnet and an Opus judge |

**Result.** The first-shown idea won **11 of 12** verdicts; the fitted
position bias is $\gamma = 1.93$ logits (87 % first-position win rate
between equal ideas). Because both orders of every pair went to different
judges and the model estimates $\gamma$, the bias did not become a fake
ranking: only I008 (crisis-correlation risk budgeting) won a pair in both
orders, and every finalist's 95 % rank interval is 1-4. The honest reading
is **not separable at this size**, with weak evidence for I008. The top-k
set also changes with the prior scale, which the report flags.

**Cost.** At least 1.41M new tokens and 6.5M cache reads, from the 35
recoverable transcripts of about 40 subagent dispatches (retries
included); the referee session is not counted. The run first reported
0.90M: the usage count kept one transcript per dispatch id, and the
generator ids repeat across three phases (fixed; DESIGN.md §14). Early phases used general-purpose subagents (the role agents had
not yet loaded in this cloud session); those cost ~55k tokens per dispatch
versus ~12-35k for the role agents.

**Issues found by the run and fixed in the code** (both have regression
tests):
- Critics who ranked all 4 cards instead of their top 3 were rejected and
  forced into full rewrites; a longer valid ranking is now truncated.
- Ideas with *fixable* gate citations were excluded from the finals as if
  barred; only barred ideas are now excluded. The run was rolled back to
  the start of the finals (no verdicts existed) and continued.

## Reruns with the fixes (2026-09-29)

Three controlled branches of the recorded run test the fixes for the problems
it exposed. Each branch replays the recording to a phase with
`brainswarm replay --until` and then re-runs the later phases with live agents,
so everything upstream (ideas, critiques, workshop slots, pairs) is
identical. `uv run python examples/rerun_comparison.py` rebuilds all of them
offline from `demo-reruns/` and recomputes the table and figure.

| Condition | What changed | First-listed wins | $\gamma$ (95 % interval) | Order |
|---|---|---|---|---|
| original | — | 11/12 | 1.93 (0.39, 3.46) | I008 > I004 > I003 > I002 |
| finals-only | judge prompt: strengths of both, named winner, cited criterion | 10/12 | 1.62 (0.13, 3.11) | I008 > I004 > I002 > I003 |
| crossover | finals-only plus each model judging the other order (24 verdicts) | 20/24 | 1.78 (0.59, 2.98) | I008 > I003 > I004 > I002 |
| from-workshop | workshop word budget, new judge prompt, crossover schedule | 8/12 | 0.89 (−0.50, 2.27) | I002 > I003 > I004 > I008 |

![Position bias and finalist strengths across the reruns](../docs/figures/position_bias.png)

*The judges' preference for the first-listed idea is real, and the prompt
change did not remove it. Left: the fitted position bias $\gamma$ per
condition (dot) with its 95 % Laplace interval; the dashed line is no bias,
and $\gamma = 1.8$ means two equal ideas are split 86 : 14 in favour of the
one listed first. Right: finalist strengths $\beta$ fitted on the same four
cards from the original 12 verdicts (orange) and the 24 crossover verdicts
(blue). The intervals overlap everywhere, so no finalist is separable from
another on these cards.*

**Position bias.** In the crossover, each model saw both orders of every
pair (in different dispatches) and changed its winner with the order in 4 of
6 pairs, for Sonnet and Opus alike. Under no bias, 20 or more first-listed
wins out of 24 has probability
$\sum_{k=20}^{24}\binom{24}{k}2^{-24} \approx 7.7\times10^{-4}$. The first
finals design sent the two orders of a pair to different models, so with
two judge dispatches it could not tell "each judge prefers the first idea"
from "the judges disagree". The schedule is now a crossover: one model
judges both orders of a pair. In the from-workshop run this gave within-model
contrasts (Sonnet flipped 0 of 3 pairs, Opus 2 of 3) and a smaller $\gamma$
whose interval includes 0. The bias matters most between near-equal ideas:
the only verdicts that survived both orders in the crossover were I008 over
I002 and I008 over I003.

**Workshop.** With a per-field word budget, all four developed cards were
within the 400-word cap at first attempt (338–383 words); the original
workshop sent three back (533, 455 and 694 words). In both workshops every
critique was answered as `fixed` (35 of 35; before, 33 fixed and 1
conceded), so the re-critique's test of whether rebuttals hold was never
used; this is on the watch list (DESIGN.md §15).

**Ranking.** The from-workshop finals put I002 first (rank interval 1–2,
mean win 90 %) and I008 last, the reverse of the original. The ideas are
the same, but their developed cards are new: I002's card changed from
"Stress-Mixture Covariance Sizing with Rank-1 PC1 Stress Prior" to
"Stress-Mixture ERC with Sign-Preserving Stress Prior and Drawdown Taper".
The rank intervals are conditional on the cards; they do not include the
variation between two workshop attempts at the same idea, which here was
larger than the variation between judges. Among four near-equal finalists,
one run's order should not be read as a verdict on the ideas.

**Cost.** Re-running the workshop, re-critique and finals took about 0.43M
new tokens; the finals-only rerun about 0.05M, and the crossover 0.05M.
