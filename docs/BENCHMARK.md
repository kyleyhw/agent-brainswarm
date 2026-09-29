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
   format do not favour either side. Each card must be self-contained: the first ETF baseline
   wrote "same harness as Idea 1", which revealed its origin, and was regenerated.
3. **Blinding.** `benchmark/make_pack.py` renders both top-3 sets in one card format without
   sources, ids or provenance, and shuffles them with a seed drawn from OS entropy by numpy.
   The seed and the label key go to `key.json`, which the judge opens only after rating.
   The builder refuses a pack whose cards mention an idea number or id (`Idea 1`, `I008`,
   `L0004`).
4. **Judging.** Every card is rated from 1 to 5 on constraint fit, drawdown (or the brief's
   main risk), growth (or the main objective), diversification (or breadth), and "would
   pursue", then all six are ranked. The default rater is a panel of six independent LLM
   reviewers (`benchmark/llm_review.py`): two each of Sonnet, Opus and Fable, each in a fresh
   read/write-only context, with card order counterbalanced by a 6x6 cyclic Latin square
   (every card once in every position) and letters reassigned per reviewer. A human rater
   (`pack.md`) remains the stronger check where one with domain knowledge is available,
   because both sides were written by Claude models and brainswarm's finalists were chosen
   by Claude judges, so LLM reviewers partly measure agreement with the system's own taste;
   the demo also showed LLM judges have a strong position bias
   ([`DESIGN.md` §10](DESIGN.md#10-scoring)).
5. **Analysis.** Per brief, the difference in mean "would pursue" score and the mean rank of
   each side. Across briefs, a sign test on the per-brief differences. With 3–5 briefs this
   detects only a large effect; the benchmark is a sanity check, not a precise estimate.

## Limitations

- **Style tells.** Workshopped brainswarm titles tend to be long and colon-separated, which a
  reader may learn to recognise, and developed cards can carry traces of the critique round
  ("conceded", "the old renormalising gate"). Both are kept verbatim because rewriting them
  would change content.
- **Selection.** Each side's top 3 is chosen by that side's own process, which is the
  intended comparison (what a user would receive), not a comparison of raw generation.
- **One rater.** A single rater's taste is confounded with the brief. More raters, or an
  outcome measured by arithmetic or backtest, would strengthen it.

## Status

| Brief | Brainswarm run | Baseline | Pack | Ratings |
|---|---|---|---|---|
| ETF strategy | recorded (`examples/demo-run/`) | done | [`benchmark/etf-strategy/pack.md`](../benchmark/etf-strategy/pack.md) | 6 LLM reviewers (below); no human rating |
| Exoplanet transit | shelved until usage allows | pending | pending | pending |
| Home heating | shelved until usage allows | pending | pending | pending |

## Results

### ETF strategy (2026-09-29)

![Ranks from six independent reviewers](figures/benchmark_etf_review.png)

*The six reviewers did not prefer either side. Each row is one card; small dots are the rank
each reviewer gave it (1 = best, right), and the large dot is the mean. Blue: brainswarm's
three finalists; orange: the single agent's own top three. The single agent's first choice has
the best mean rank (2.17) and its third choice the worst (5.17); brainswarm's cards sit in
between (2.50, 3.67, 4.00). The spread of dots within every row is wide: the reviewers agree
only weakly.*

| Measure | Brainswarm minus single agent | Reviewers favouring brainswarm | Sign test p |
|---|---|---|---|
| "Would pursue" (1–5) | 0.00 | 3 of 6 | 1.0 |
| Rank (lower is better) | −0.22 | 3 of 6 | 1.0 |

- **Agreement** between reviewers is weak: Kendall's $W = 0.33$ (0 = none, 1 = identical
  rankings).
- **Model effect:** both Opus reviewers preferred brainswarm (rank differences −3.00 and
  −1.00), both Fable reviewers preferred the single agent (+1.67, +3.00), and the Sonnet
  reviewers split. With two reviewers per model this is suggestive only.
- **Position:** the Spearman correlation between the order a card was shown in and its rank
  is 0.22 (cards shown earlier ranked slightly better); the Latin square spreads this evenly
  over both sides.
- **Reading.** On this brief, at this reduced size and with web research off, brainswarm's
  finalists were not rated better than a single strong agent's own top three, at about 24
  times the new-token cost. One brief is not a verdict on the method; the physically
  checkable briefs are the stronger test.

## Cost

The ETF baseline agent used 59k new tokens and 0.15M cache reads in one dispatch (the
regenerated, self-contained baseline about the same), against at
least 1.41M new tokens and 6.5M cache reads for the recorded brainswarm run (35 recovered
transcripts, web off): a ratio of about 24 in new tokens. Both are measured from subagent
transcripts with the same accounting (`usage.py`).
