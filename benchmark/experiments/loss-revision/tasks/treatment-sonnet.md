# Idea revision task

You revise idea cards for a system that generates ideas for the brief below. Read no file other than this one.

## Brief

Ways to make a multi-agent idea-generation system (independent generators, justified critique, development of selected ideas, LLM-judged pairwise finals) produce top ideas that measured outcomes or independent raters prefer over a single strong agent's self-selected top 3 for the same brief. Hard rules: each change must be implementable in this codebase and testable with the existing benchmark.

## Idea I001

```json
{
 "title": "Boundary-targeted help budget with survivor-mutation cycles",
 "pitch": "Spend critique and mutation calls only on ideas whose rank interval straddles the top-3 cutoff, and re-enter their single-edit mutants for up to 3 cycles.",
 "mechanism": "New phase MATURE between critique and finals. Round 0: order-swapped pairwise judging against the frozen brief-plus-rubric; fit Bradley-Terry; bootstrap rank intervals. Up to H=6 ideas straddling rank 3/4 each get one critique naming their weakest criterion, then one mutator call writing k=3 same-length single-edit variants. A variant replaces its parent only if it beats the parent and the rank-3 incumbent. Refit and repeat.",
 "rationale": "Top-k identification bandits (LUCB; Kalyanakrishnan et al. 2012) need far fewer samples when effort concentrates near the cutoff; MATURE concentrates refinement the same way. A lone agent lacks an independent signal: models favour their own outputs (Panickssery et al. 2024) and self-correct poorly without external feedback (Huang et al. 2023). No code was run.",
 "assumptions": [
  "In-loop judge preferences track the independent panel's",
  "Single targeted edits help more often than they harm",
  "Some ideas sit near the cutoff"
 ],
 "failure_modes": [
  "Mutants overfit the in-loop judge; mitigate with a judge family different from the panel and a 10% length cap",
  "Sparse round-0 data widens every interval, so H does all the selecting",
  "Partial transfer: real germinal centres give most help to top clones (Gitlin et al. 2014), not boundary ones",
  "Mutants converge to near-duplicates"
 ],
 "cheapest_test": "10 briefs, equal tokens: MATURE versus uniform development of the point-estimate top 6. Primary: blinded, counterbalanced benchmark win rate against the single agent's top 3. Secondary: child-beats-parent rate under a held-out judge family.",
 "effort": "3-5 days; per cycle about 6 critiques, 6 mutator calls and 72 short judge calls; roughly +30-50% run cost.",
 "spec": "Round 0: 3 comparisons per idea, both orders. Existing BT module, 200 bootstrap resamples, 10th-90th percentile rank interval. Boundary: lo<=3 and hi>=4; keep 6 with P(top3) nearest 0.5. Accept a variant iff it wins both orderings against its parent and one against the rank-3 incumbent. Max 3 cycles; stop when the boundary set is unchanged."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I001's mutants are accepted by in-loop LLM judge preference and so may drift toward whatever that judge rewards (its own admitted overfitting risk), whereas I007 is built to absorb length, polish and family-match effects into terms that are explicitly not rewarded and validates against external blinded outcomes.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 362 words in total (the original has 345).

## Idea I007

```json
{
 "title": "Residual selection head learned from the library's blinded verdicts",
 "pitch": "Replace the final top-3 cut with a regularised logistic model, trained on past blinded benchmark verdicts, that predicts which finalists beat the baseline.",
 "mechanism": "The library stores per finalist x: internal BT strength (z-scored per run), per-criterion critic scores, development score delta, generator id, max cosine similarity to library ideas, and nuisance covariates (word count, citation/hedge counts, judge-generator family match). Label: fraction of counterbalanced external comparisons it wins against the baseline's three cards. Residual model: logit p = beta0*BT + w.x, beta0 fixed at the current internal weight, w ~ N(0, sigma^2), so with few labels it reduces to today's ranking.",
 "rationale": "Length-controlled AlpacaEval (Dubois et al. 2024) regresses preferences on length and zeroes that term, removing much verbosity bias; this applies it to selection. Zheng et al. 2023 and Panickssery et al. 2024 document the verbosity, position and self-preference biases the covariates target. Si et al. 2024 found LLM idea rankings agree weakly with experts, so internal ranking error exists to learn. A lone agent never sees its own selection error. No code run (sandbox unavailable).",
 "assumptions": [
  "At least ~15 benchmarked briefs with all finalists labelled",
  "Selection error is partly systematic across briefs",
  "Training labels come from humans or a model family different from the eval panel"
 ],
 "failure_modes": [
  "Labels from the eval panel teach its biases (Goodhart)",
  "Brief heterogeneity swamps ~10 labels per brief",
  "Generator changes shift the distribution"
 ],
 "cheapest_test": "Offline on existing runs: panel-rate all finalists once (~10 x 3 baseline cards x 2 orders). Compare leave-one-brief-out AUC and top-3 win rate, calibrated vs internal BT. No new generation.",
 "effort": "~4 days: schema, labelling job, ~80-line NumPy IRLS fit, switch. Benchmark panel cost doubles once; run cost unchanged.",
 "spec": "select_by in {internal_BT, calibrated}. Binomial log-likelihood on (wins, trials), L2 lambda=1 on w, per-run z-scored features; label weight 3 for human/measured, 1 for panel. At selection, zero nuisance terms so they absorb bias without being rewarded. Fall back to internal_BT below 15 labelled briefs. Evaluate by leave-one-brief-out log-loss/AUC, then top-3 win rate on later briefs with a different-family panel."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I007 can only reorder an existing finalist pool and does nothing until ~15 benchmarked briefs are labelled (with a Goodhart risk if the labels come from the eval panel), whereas I001 improves the top-3 candidates themselves at the development stage within a single run, with an on/off equal-token test and a held-out-family child-beats-parent check.
- I005 changes what survives critique using tool-grounded evidence a single agent cannot supply, while I007 only re-ranks finalists and needs 15+ labelled briefs and non-panel labels that may not exist.
- I005 adds grounded verification at the critique and selection stages, which a single self-selecting agent cannot do, and it withholds the prose that biases judges. I007 needs at least 15 labelled briefs, risks learning the panel's biases, and is unlikely to move the top 3 much from about 10 labels per brief.
- I007 is trained on benchmark verdicts, so from about 15 noisy briefs it mostly learns what the benchmark panel prefers, which puts it at risk of helping only on the benchmark. I006 makes the delivered ideas more correct on any brief whose claims can be checked.
- I007 learns to predict what beats the baseline under the benchmark panel. It needs at least 15 labelled briefs before it switches on, and it risks Goodhart overfitting to the raters. I006 makes the delivered ideas more likely to be correct on any brief with checkable claims, so its benefit extends beyond the benchmark.
- I004 makes the finalist cards themselves better, which carries to any brief a user submits, whereas I007 only reorders the existing finalists against labels defined by the benchmark comparison, so its ceiling is the quality of the pool and its gain risks being specific to the benchmark's rater panel (the Goodhart failure it names itself).
- I004 names a stage (development) and a concrete reason a single agent cannot match it (loss reasons from independent judges, gated by an independent verifier), whereas I007's gain rests on the untested assumption that selection error is systematic and learnable from roughly 15 briefs of benchmark labels, with a Goodhart risk that the head learns the labelling panel's preferences rather than idea quality.
- I008 estimates and removes position and self-preference bias per judge and downweights judges that disagree with independent raters, so its correction is tied to judge behaviour that plausibly transfers across briefs, whereas I007 fits directly to the benchmark's external verdicts and can only neutralise the biases it has pre-enumerated as covariates while risking encoding the labelling panel's own preferences.
- I003 is a clean on/off scoring switch with a named primary metric (best-of-3) testable on existing data at almost no cost, whereas I007 needs at least 15 labelled briefs, is fragile to Goodhart effects when labels come from the panel, and will be swamped by brief heterogeneity at about 10 labels per brief.
- I003 improves the selection stage with a concrete mechanism (best-of-3 under correlated same-lever ideas) that is cheap and testable on saved data, whereas I007 needs 15 or more labelled briefs, faces Goodhart risk from panel-derived labels, and is likely to be swamped by brief heterogeneity.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 374 words in total (the original has 357).

## Idea I008

```json
{
 "title": "Judge-reliability Bradley-Terry fitted to external verdicts",
 "pitch": "Weight each finals judge by how well its votes predicted independent raters on past runs, and spend the fixed comparison budget on reliable judges near the top-3 boundary.",
 "mechanism": "Judge j is a (model, prompt variant) pair. Vote model: P(i>k | j, i first) = sigmoid(a_j(theta_i - theta_k) + b_j + c_j(f_ij - f_kj)); a_j is discrimination, b_j position bias, f_ij = 1 if idea i's generator shares judge j's family (self-preference). Fit: fix theta of past finalists to external BT strengths, fit (a_j, b_j, c_j) by MAP with priors N(1,0.5), N(0,0.5), N(0,0.5), then freeze. At runtime estimate theta by MAP with N(0,1) prior, subtracting b_j and c_j terms.",
 "rationale": "Crowd-BT (Chen et al. 2013) and Dawid-Skene (1979) show reliability-weighted aggregation beats uniform weighting. PoLL (Verga et al. 2024) shows judges differ in agreement with humans. Zheng et al. 2023 and Panickssery et al. 2024 show position and self-preference biases are measurable. A lone agent is one judge with unknown a and uncorrected b, c. No code run (sandbox unavailable).",
 "assumptions": [
  "Judge reliability is stable across briefs",
  "At least ~300 past internal votes on externally rated ideas",
  "External reference differs from the evaluation panel"
 ],
 "failure_modes": [
  "Noisy a_j estimates add variance",
  "If all judges are equally weak, it reduces to uniform with no gain",
  "Judge model updates invalidate frozen parameters"
 ],
 "cheapest_test": "Offline refit on existing runs: compare held-out-brief pairwise agreement with external rankings and Kendall tau of theta vs external strengths, uniform vs judge-aware BT at equal vote count.",
 "effort": "~3 days: scoring-module extension and scheduler change. Zero extra tokens at equal budget.",
 "spec": "judge_model in {uniform, reliability}. Of fixed budget B, 10% uniform across judges (monitoring); 90% to pairs among current top 6 with |theta_i - theta_k| < 0.5, judges sampled proportional to max(a_j,0)^2 (Fisher information per vote). Every pair shown in both orders. Refit a, b, c after each benchmark batch."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I003 needs no hundreds of past external-labelled votes or stable judge reliability, and it improves what users get on any brief by delivering a portfolio, whereas I008's gain depends on untested judge stability and can reduce to uniform weighting.
- I003 is a single switch that can be replayed on saved pairwise records and panel ratings and scored on best-of-3, mean-of-3 and cluster count. I008 needs about 300 past votes and stable judge reliability before it can be fitted, and its gain over uniform weighting is likely small.
- I008 can only reweight judges and correct position and self-preference, so a bias shared by every LLM judge (verbosity, polish) passes through untouched, whereas I007 models those nuisance features directly and zeroes them at selection, so its gain is by construction not earned by longer or more polished cards.
- I006 improves the content of the ideas through development, with an outcome measured by a held-out checker and a cross-run compounding effect a single agent cannot match, while I008 only reweights the selection votes, which likely gives a small gain when the judges are similar and depends on about 300 externally rated past votes.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 342 words in total (the original has 326).

## Idea I002

```json
{
 "title": "Cross-run memory of mutation-operator success, chosen by similarity-weighted Thompson sampling",
 "pitch": "Store each parent-versus-child contest as a measured win or loss for a typed edit operator in the idea library, and in later runs pick operators by Thompson sampling over brief-similar history.",
 "mechanism": "The mutator labels each variant with one operator from a fixed taxonomy: narrow scope, swap mechanism, add falsifiable test, graft a rival's strongest component, invert an assumption, cut cost, change target user, quantify the claim. Each contest writes a record (brief embedding, operator, targeted criterion, win/loss, judge model). The run's top 3 are the 'plasma' output; operator statistics are the 'memory'. At mutation time, for the idea's weak criterion, compute alpha=1+sum(sim*wins) and beta=1+sum(sim*losses) over records with cosine sim>=0.6 and the same criterion, then sample to choose operators.",
 "rationale": "Bandit-based adaptive operator selection is established in evolutionary computation (Fialho et al. 2010). PromptBreeder (Fernando et al. 2023) shows evolving mutation instructions helps. The new part is conditioning across runs on brief similarity. Ideas rarely transfer between briefs, but good edit moves may.",
 "assumptions": [
  "Operator efficacy generalises across similar briefs",
  "Operator labels are applied faithfully",
  "Card 0's contest loop exists"
 ],
 "failure_modes": [
  "Effects too small to detect within a few dozen runs",
  "Memory learns in-loop judge quirks, not quality",
  "Exploitation collapses operator diversity (guard: 1 of 3 slots uniform-random)",
  "Stretch transfer: immune memory stores binders, not edit types"
 ],
 "cheapest_test": "Warm the library with 20 training briefs using uniform operators. Run 30 held-out briefs in both arms, memory on versus uniform, at equal cost. Primary measured outcome: child-beats-parent rate (about 540 contests per arm; a 40%-to-50% difference needs about 390 per arm at 80% power, hand-calculated). Secondary: benchmark win rate.",
 "effort": "2-3 days on top of card 0; negligible token cost (one embedding per brief).",
 "spec": "Library table operator_outcomes(run_id, brief_emb, operator, criterion, win, judge). Similarity threshold 0.6; fall back to all records when fewer than 10 match. Thompson draws pick 2 operators, the third is uniform-random. Contest rule as in card 0."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I002 presupposes a mutation-contest loop that does not yet exist and needs roughly 50 full runs (20 warm-up plus 30 held-out) before its effect could be seen, whereas I007 can be built and evaluated on already-completed runs in about four days.
- I002 itself admits its effect may be too small to detect within a few dozen runs and only tunes which edit operator is tried, while I006 directly changes the content of the top-3 cards by making their claims survive execution, a gain a lone agent without prior runs and an external checker cannot reproduce.
- I002 by its own account may be undetectable within a few dozen runs and yields nothing until 20 training briefs have been run, while I006 produces a development-stage improvement on the first run through pass-or-strike repair against executed checks, even though both inherit a dependency on a card-0 loop.
- I007's effect can be isolated today with a one-time panel labelling of existing finalists and a leave-one-brief-out comparison against internal BT, whereas I002 needs I001's contest loop built first and about 50 fresh brief runs before its admittedly small effect could be detected.
- I008 is built to remove known judge biases and calibrate to external raters, whereas I002 depends on an unbuilt contest loop, needs a warm-up of 20 briefs, and risks learning in-loop judge quirks with effects too small to detect.
- I008 directly improves the final selection using external verdicts and bias correction, and it is testable offline. I002 depends on an unbuilt contest loop, needs hundreds of contests to detect small effects, and its win/loss labels come from the in-loop judge, so it may learn that judge's quirks rather than quality.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 354 words in total (the original has 338).

## Output

Write one JSON object to `/home/user/agent-brainswarm/benchmark/experiments/loss-revision/out/treatment-sonnet.json`: {"revisions": {"<idea id>": {<the card fields: title, pitch, mechanism, rationale, assumptions (list), failure_modes (list), cheapest_test, effort, spec>}}}, with one entry for every idea above.
