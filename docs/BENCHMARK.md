# Benchmark protocol

This protocol asks whether a brainswarm run produces better top ideas than a single strong
agent given the same brief. It is Phase 6, task 20 of [`PROJECT_PLAN.md`](../PROJECT_PLAN.md).

## Hypothesis

Let $Q(x)$ be a judge's score for idea $x$. For a brief $b$, let $S_b$ be brainswarm's top
$k$ finalists and $B_b$ the single agent's own top $k$. The claim under test is

$$
\mathbb E\big[\bar Q(S_b)\big] > \mathbb E\big[\bar Q(B_b)\big],
$$

where $\bar Q$ is the mean score of a set. The claim is judged against cost: a brainswarm run
used about 24x the new tokens of the baseline on the ETF brief (§ Cost), more with web research on, so a small quality gain may not be
worth it.

## Design

1. **Briefs.** 3–5 concrete briefs with stated constraints. The first three are the demo
   manifests in [`examples/demos/`](../examples/demos/). The exoplanet-transit and home-heating
   briefs were chosen because part of their quality is checkable by arithmetic (a photometric
   noise budget; a heat-loss calculation), which gives a measurable outcome alongside the
   human rating.
2. **Baseline.** One Opus agent per brief with the task in
   `benchmark/<brief>/baseline_task.md`: 20 ideas with a two-sentence pitch each, then its own
   top 3 developed into full cards. It has the same web setting as the brainswarm run and the
   same card fields and 400-word cap as brainswarm's workshopped finalists, so length and
   format do not favour either side.
3. **Blinding.** `benchmark/make_pack.py` renders both top-3 sets in one card format without
   sources, ids or provenance, and shuffles them with a seed drawn from OS entropy by numpy.
   The seed and the label key go to `key.json`, which the judge opens only after rating.
4. **Judging.** A human rates every card from 1 to 5 on constraint fit, drawdown (or the
   brief's main risk), growth (or the main objective), diversification (or breadth), and
   "would pursue", then ranks all six. Human raters are used because the demo showed LLM
   judges have a strong position bias ([`DESIGN.md` §10](DESIGN.md#10-scoring)).
5. **Analysis.** Per brief, the difference in mean "would pursue" score and the mean rank of
   each side. Across briefs, a sign test on the per-brief differences. With 3–5 briefs this
   detects only a large effect; the benchmark is a sanity check, not a precise estimate.

## Limitations

- **Style tells.** Workshopped brainswarm titles tend to be long and colon-separated, which a
  reader may learn to recognise. Titles are kept verbatim because rewriting them would change
  content.
- **Selection.** Each side's top 3 is chosen by that side's own process, which is the
  intended comparison (what a user would receive), not a comparison of raw generation.
- **One rater.** A single rater's taste is confounded with the brief. More raters, or an
  outcome measured by arithmetic or backtest, would strengthen it.

## Status

| Brief | Brainswarm run | Baseline | Pack | Ratings |
|---|---|---|---|---|
| ETF strategy | recorded (`examples/demo-run/`) | done | [`benchmark/etf-strategy/pack.md`](../benchmark/etf-strategy/pack.md) | awaiting a human rater |
| Exoplanet transit | shelved until usage allows | pending | pending | pending |
| Home heating | shelved until usage allows | pending | pending | pending |

## Cost

The ETF baseline agent used 59k new tokens and 0.15M cache reads in one dispatch, against at
least 1.41M new tokens and 6.5M cache reads for the recorded brainswarm run (35 recovered
transcripts, web off): a ratio of about 24 in new tokens. Both are measured from subagent
transcripts with the same accounting (`usage.py`).
