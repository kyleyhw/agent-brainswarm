# Pairwise judgement task

For each pair, decide which version of the idea you would rather pursue for the brief below. Judge substance, not length or polish; the order carries no information. Read no file other than this one.

## Brief

Ways to make a multi-agent idea-generation system (independent generators, justified critique, development of selected ideas, LLM-judged pairwise finals) produce top ideas that measured outcomes or independent raters prefer over a single strong agent's self-selected top 3 for the same brief. Hard rules: each change must be implementable in this codebase and testable with the existing benchmark.

## Pair p01

## Idea X: Loss-conditioned revision under a fixed card budget with a two-order verifier gate

**Pitch.** Give each finalist's developer the judges' reasons for its losses, allow only a same-length revision, and accept it only if a different-family judge prefers it in both orderings.

**Mechanism.** After the first pairwise round: (1) Take up to 5 reasons from each finalist's losses; a filter drops reasons praising the opponent rather than faulting this card. (2) The developer fixes only the cited weaknesses, keeping the mechanism, within +/-5% of the original token count (Python check; one retry, else the original stays). (3) A blinded verifier from a family outside generator, developer and final panel compares revised vs original in both orders and rates ambition 1-5. Accept only if the revision wins both orders without lower ambition. (4) Drop the original's comparisons, replay the same opponents with the revision, refit PL.

**Rationale.** Unverified self-revision often fails (Huang et al. 2023); Self-Refine gains (Madaan et al. 2023) need useful feedback. Here feedback is an independent adversary's reasons and the gate makes the loop monotone in verifier preference. Length matching and two-order acceptance counter verbosity and position bias (Zheng et al. 2023). A lone agent has no independent losses. Citations from memory.

**Assumptions.** Filtered judge reasons identify real weaknesses; The verifier's preference correlates with final raters' preference; A 5% budget leaves room for substantive fixes

**How it fails.** Revisions cut ambition; the ambition rating guards this; Acceptance rate near zero, so no effect; Any revision helps equally; the no-reasons arm detects this

**Cheapest test.** On 20 briefs' existing finalists, run revise plus gate; report acceptance rate. A third-family panel rates accepted revisions vs originals, blinded. A no-reasons revision arm, same gate, isolates conditioning. Kill if acceptance < 10%, panel preference for accepted revisions < 55%, or loss-conditioning fails to beat no-reasons.

**Effort.** About 1 week: sub-phase, reason filter, length check, verifier prompt, PL replay. Roughly +25% run cost.

**Operational spec.** revise(card, filter(reasons)[:5], budget=0.95-1.05 x tokens) -> verify(revised, original, family not in {gen, dev, panel}, orders AB and BA) -> accept iff both wins, ambition not lower -> replay opponents, refit PL. Arms: unrevised, no-reasons, loss-conditioned.


## Idea Y: Loss-conditioned revision under a fixed card budget with a two-order verifier gate

**Pitch.** Give each finalist's developer the judges' reasons for its losses, allow only a same-length revision, and accept it only if a different-family judge prefers it in both orderings.

**Mechanism.** Development sub-phase after the first pairwise round. (1) Collect up to 5 written reasons from each finalist's lost comparisons. (2) The developer gets the card plus those reasons and must fix only the cited weaknesses, keeping the mechanism, within +/-5% of the original token count (Python check; one retry, else the original stays). (3) A judge from a family different from generator and developer compares revised vs original in both orders, blinded. Accept only if the revision wins both. (4) Accepted revisions replace originals in the PL fit; rerun comparisons for changed items only.

**Rationale.** Unverified self-revision often fails to help (Huang et al. 2023); Self-Refine gains (Madaan et al. 2023) depend on useful feedback. Here the feedback is an independent adversary's reasons, and the gate makes the loop monotone in a verifier's preference. Length matching and both-order acceptance target verbosity and position bias (Zheng et al. 2023). A lone agent has no independent losses to condition on. Cited from memory; web was off.

**Assumptions.** Stated judge reasons identify real weaknesses; The verifier's preference correlates with final raters' preference; A 5% budget leaves room for substantive fixes

**How it fails.** Revisions fix what judges say but cut ambition; Acceptance rate near zero, so no effect; Verifier and final panel share a family, reinforcing its style

**Cheapest test.** On 20 briefs from existing finalist sets, run revise plus gate and report the acceptance rate. A third-family panel rates accepted revisions vs originals, blinded. A control arm revising without loss reasons isolates the value of conditioning.

**Effort.** About 1 week: new sub-phase, length check, verifier prompt, PL replacement handling. Roughly +25% run cost.

**Operational spec.** revise(card, loss_reasons[:5], budget=0.95-1.05 x tokens) -> verify(revised, original, family not in {gen, dev}, orders AB and BA) -> accept iff both wins -> replace in PL. Arms: unrevised, no-reasons revision, loss-conditioned.


## Pair p02

## Idea X: Top-3 chosen as a portfolio by posterior expected maximum with mechanism clusters

**Pitch.** Replace 'take the 3 highest Bradley-Terry scores' with a set-selection rule that maximises the expected best idea among the delivered 3.

**Mechanism.** Scoring-module change only. (1) Bootstrap pairwise records (B=2000), refit BT/PL with a weak ridge prior to get score samples s_b[i]; items under 4 comparisons are ineligible (variance-seeking guard). (2) One cheap call labels each finalist's core lever (not topic) from a closed list of at most 6. (3) Add a shared cluster shift s_b[i] += tau*z_b[c(i)], z ~ N(0,1), so same-lever ideas succeed or fail together; tau^2 = within-cluster covariance of residuals (panel rating minus BT score) on saved runs, leave-one-brief-out; default 0.5 x pooled SD. (4) Greedy: start from the top mean, then repeatedly add the item maximising mean_b[max over set of s_b]; ties within 1 SE go to a new cluster.

**Rationale.** A user mostly needs one good idea, and best-of-k value depends on variance and correlation, not only the mean (Girotra, Terwiesch, Ulrich 2010). MMR reranking (Carbonell and Goldstein 1998) likewise penalises redundant picks. A single agent picking 3 of its own ideas tends to choose variants of one theme and has no posterior. Citations from memory.

**Assumptions.** Same-lever ideas have positively correlated rating residuals (measured when fitting tau); Cluster labels are consistent (kappa >= 0.6 over two runs, else top-3); The comparison bootstrap approximates real score uncertainty

**How it fails.** If the metric is mean-of-3, diversification loses by construction; pre-register best-of-3 as primary; Finalists already diverse, so a null result; Noisy labels make the tie-break random

**Cheapest test.** Offline replay of saved pairwise records and panel ratings: both selections per brief, compared on best-of-3, mean-of-3 and distinct clusters by paired bootstrap over briefs. Kill if selections differ on under 20% of briefs or the best-of-3 gain's 95% interval includes zero.

**Effort.** 2-3 days: about 60 lines of NumPy, one prompt, one config flag.

**Operational spec.** select_top3(records, labels, B=2000, tau=fit_or(0.5*sd_pooled), k=3, tie_se=1.0, min_comp=4). Flag portfolio_select on/off. Metrics: best-of-3 rating, mean-of-3, distinct clusters.


## Idea Y: Top-3 chosen as a portfolio by posterior expected maximum with mechanism clusters

**Pitch.** Replace 'take the 3 highest Bradley-Terry scores' with a set-selection rule that maximises the expected best idea among the delivered 3.

**Mechanism.** Scoring-module change only. (1) Bootstrap the pairwise records B=2000 times and refit BT/PL with a weak ridge prior to get score samples s_b[i]. (2) One cheap call labels each finalist with a mechanism cluster (the core lever pulled, not the topic), from a closed list of at most 6. (3) Add a shared cluster shift s_b[i] += tau*z_b[c(i)], z ~ N(0,1), tau = 0.5 x pooled score SD, so same-lever ideas succeed or fail together. (4) Greedy: take the highest mean score, then repeatedly add the item maximising mean_b[max over set of s_b]; ties within 1 SE go to a new cluster.

**Rationale.** A user mostly needs one good idea, and best-of-k value depends on variance and correlation, not only the mean (Girotra, Terwiesch, Ulrich 2010). Top-k by score ignores correlated duplicates; MMR reranking (Carbonell and Goldstein 1998) targets the same problem. A single agent picking 3 of its own 20 tends to choose variants of its favourite theme and has no posterior. Cited from memory; web was off.

**Assumptions.** Same-lever ideas have positively correlated ratings (checkable on existing data); Cluster labels are consistent; The comparison bootstrap approximates real score uncertainty

**How it fails.** If the metric is mean rating of the top 3, diversification loses by construction; make best-of-3 primary; Finalists already diverse, so a null result; Noisy labels make the tie-break random

**Cheapest test.** Offline replay on saved pairwise records and panel ratings: compute both selections per brief, compare best-of-3, mean-of-3 and distinct clusters with a paired bootstrap over briefs. Cost: one labelling call per brief.

**Effort.** 2-3 days: about 60 lines of NumPy, one prompt, one config flag.

**Operational spec.** select_top3(records, labels, B=2000, tau=0.5*sd_pooled, k=3, tie_se=1.0). Flag portfolio_select on/off. Metrics: best-of-3 rating, mean-of-3, distinct clusters.


## Pair p03

## Idea X: Boundary-targeted help budget with survivor-mutation cycles

**Pitch.** Spend critique and mutation calls only on ideas whose rank interval straddles the top-3 cutoff, and re-enter their single-edit mutants for up to 3 cycles.

**Mechanism.** New phase MATURE between critique and finals. Round 0: order-swapped pairwise judging against the frozen brief-plus-rubric; fit Bradley-Terry; bootstrap rank intervals. Up to H=6 ideas straddling rank 3/4 each get one critique naming their weakest criterion, then one mutator call writing k=3 same-length single-edit variants. A variant replaces its parent only if it beats the parent and the rank-3 incumbent. Refit and repeat. Finals re-rank on fresh comparisons, avoiding winner's-curse selection.

**Rationale.** Top-k identification bandits (LUCB; Kalyanakrishnan et al. 2012) need far fewer samples when effort concentrates near the cutoff; MATURE concentrates refinement the same way. A lone agent lacks an independent signal: models favour their own outputs (Panickssery et al. 2024) and self-correct poorly without external feedback (Huang et al. 2023). No code was run.

**Assumptions.** In-loop judge preferences track the independent panel's; Single targeted edits help more often than they harm; Some ideas sit near the cutoff

**How it fails.** Mutants overfit the in-loop judge; mitigate with a judge family different from the panel and a 10% length cap; Sparse round-0 data widens every interval, so H does all the selecting; Partial transfer: real germinal centres give most help to top clones (Gitlin et al. 2014), not boundary ones; Mutants converge to near-duplicates

**Cheapest test.** 10 briefs, equal tokens: MATURE versus uniform development of the point-estimate top 6. Primary: blinded, counterbalanced benchmark win rate against the single agent's top 3. Secondary: child-beats-parent rate under a held-out judge family (kill if below 50%).

**Effort.** 3-5 days; per cycle about 6 critiques, 6 mutator calls and 72 short judge calls; +30-50% run cost.

**Operational spec.** Round 0: 3 comparisons per idea, both orders. BT module, 200 bootstrap resamples, 10th-90th percentile rank interval. Boundary: lo<=3 and hi>=4; keep 6 with P(top3) nearest 0.5. Accept a variant iff it wins both orderings against its parent and one against the rank-3 incumbent. Max 3 cycles; stop when the boundary set is unchanged.


## Idea Y: Boundary-targeted help budget with survivor-mutation cycles

**Pitch.** Spend critique and mutation calls only on ideas whose rank interval straddles the top-3 cutoff, and re-enter their single-edit mutants for up to 3 cycles.

**Mechanism.** New phase MATURE between critique and finals. Round 0: order-swapped pairwise judging against the frozen brief-plus-rubric; fit Bradley-Terry; bootstrap rank intervals. Up to H=6 ideas straddling rank 3/4 each get one critique naming their weakest criterion, then one mutator call writing k=3 same-length single-edit variants. A variant replaces its parent only if it beats the parent and the rank-3 incumbent. Refit and repeat.

**Rationale.** Top-k identification bandits (LUCB; Kalyanakrishnan et al. 2012) need far fewer samples when effort concentrates near the cutoff; MATURE concentrates refinement the same way. A lone agent lacks an independent signal: models favour their own outputs (Panickssery et al. 2024) and self-correct poorly without external feedback (Huang et al. 2023). No code was run.

**Assumptions.** In-loop judge preferences track the independent panel's; Single targeted edits help more often than they harm; Some ideas sit near the cutoff

**How it fails.** Mutants overfit the in-loop judge; mitigate with a judge family different from the panel and a 10% length cap; Sparse round-0 data widens every interval, so H does all the selecting; Partial transfer: real germinal centres give most help to top clones (Gitlin et al. 2014), not boundary ones; Mutants converge to near-duplicates

**Cheapest test.** 10 briefs, equal tokens: MATURE versus uniform development of the point-estimate top 6. Primary: blinded, counterbalanced benchmark win rate against the single agent's top 3. Secondary: child-beats-parent rate under a held-out judge family.

**Effort.** 3-5 days; per cycle about 6 critiques, 6 mutator calls and 72 short judge calls; roughly +30-50% run cost.

**Operational spec.** Round 0: 3 comparisons per idea, both orders. Existing BT module, 200 bootstrap resamples, 10th-90th percentile rank interval. Boundary: lo<=3 and hi>=4; keep 6 with P(top3) nearest 0.5. Accept a variant iff it wins both orderings against its parent and one against the rank-3 incumbent. Max 3 cycles; stop when the boundary set is unchanged.


## Pair p04

## Idea X: Residual selection head learned from the library's blinded verdicts

**Pitch.** Replace the final top-3 cut with a regularised logistic model, trained on past blinded benchmark verdicts, that predicts which finalists beat the baseline.

**Mechanism.** The library stores per finalist x: internal BT strength (z-scored per run), per-criterion critic scores, development score delta, generator id, max cosine similarity to library ideas, and nuisance covariates (word count, citation/hedge counts, judge-generator family match). Label: fraction of counterbalanced external comparisons it wins against the baseline's three cards. Residual model: logit p = beta0*BT + w.x, beta0 fixed at the current internal weight, w ~ N(0, sigma^2), so with few labels it reduces to today's ranking.

**Rationale.** Length-controlled AlpacaEval (Dubois et al. 2024) regresses preferences on length and zeroes that term, removing much verbosity bias; this applies it to selection. Zheng et al. 2023 and Panickssery et al. 2024 document the verbosity, position and self-preference biases the covariates target. Si et al. 2024 found LLM idea rankings agree weakly with experts. A lone agent never sees its own selection error. No code run.

**Assumptions.** At least ~15 benchmarked briefs with all finalists labelled; Selection error is partly systematic across briefs; Training labels come from humans or a model family different from the eval panel

**How it fails.** Labels from the eval panel teach its biases (Goodhart); Brief heterogeneity swamps ~10 labels per brief; Generator changes shift the distribution

**Cheapest test.** Offline on existing runs: rate all finalists with two different-family panels (~10 x 3 baseline cards x 2 orders each); fit on panel A, score on B. Compare leave-one-brief-out AUC and top-3 win rate, calibrated vs internal BT. Kill if the AUC-gain bootstrap interval over briefs includes 0. No new generation.

**Effort.** ~4 days: schema, labelling job, ~80-line NumPy IRLS fit, switch. Benchmark panel cost doubles once; run cost unchanged.

**Operational spec.** select_by in {internal_BT, calibrated}. Binomial log-likelihood on (wins, trials), L2 lambda=1 on w, per-run z-scored features; label weight 3 for human/measured, 1 for panel. At selection, zero nuisance terms so they absorb bias without being rewarded. Fall back to internal_BT below 15 labelled briefs. Evaluate top-3 win rate on later briefs with a different-family panel.


## Idea Y: Residual selection head learned from the library's blinded verdicts

**Pitch.** Replace the final top-3 cut with a regularised logistic model, trained on past blinded benchmark verdicts, that predicts which finalists beat the baseline.

**Mechanism.** The library stores per finalist x: internal BT strength (z-scored per run), per-criterion critic scores, development score delta, generator id, max cosine similarity to library ideas, and nuisance covariates (word count, citation/hedge counts, judge-generator family match). Label: fraction of counterbalanced external comparisons it wins against the baseline's three cards. Residual model: logit p = beta0*BT + w.x, beta0 fixed at the current internal weight, w ~ N(0, sigma^2), so with few labels it reduces to today's ranking.

**Rationale.** Length-controlled AlpacaEval (Dubois et al. 2024) regresses preferences on length and zeroes that term, removing much verbosity bias; this applies it to selection. Zheng et al. 2023 and Panickssery et al. 2024 document the verbosity, position and self-preference biases the covariates target. Si et al. 2024 found LLM idea rankings agree weakly with experts, so internal ranking error exists to learn. A lone agent never sees its own selection error. No code run (sandbox unavailable).

**Assumptions.** At least ~15 benchmarked briefs with all finalists labelled; Selection error is partly systematic across briefs; Training labels come from humans or a model family different from the eval panel

**How it fails.** Labels from the eval panel teach its biases (Goodhart); Brief heterogeneity swamps ~10 labels per brief; Generator changes shift the distribution

**Cheapest test.** Offline on existing runs: panel-rate all finalists once (~10 x 3 baseline cards x 2 orders). Compare leave-one-brief-out AUC and top-3 win rate, calibrated vs internal BT. No new generation.

**Effort.** ~4 days: schema, labelling job, ~80-line NumPy IRLS fit, switch. Benchmark panel cost doubles once; run cost unchanged.

**Operational spec.** select_by in {internal_BT, calibrated}. Binomial log-likelihood on (wins, trials), L2 lambda=1 on w, per-run z-scored features; label weight 3 for human/measured, 1 for panel. At selection, zero nuisance terms so they absorb bias without being rewarded. Fall back to internal_BT below 15 labelled briefs. Evaluate by leave-one-brief-out log-loss/AUC, then top-3 win rate on later briefs with a different-family panel.


## Pair p05

## Idea X: Judge-reliability Bradley-Terry fitted to external verdicts

**Pitch.** Weight each finals judge by how well its votes predicted independent raters on past runs, and spend the fixed comparison budget on reliable judges near the top-3 boundary.

**Mechanism.** Judge j is a (model, prompt variant) pair. Vote model: P(i>k | j, i first) = sigmoid(a_j(theta_i - theta_k) + b_j + c_j(f_ij - f_kj)); a_j is discrimination, b_j position bias, f_ij = 1 if idea i's generator shares judge j's family (self-preference). Fit: fix theta of past finalists to external BT strengths, fit (a_j, b_j, c_j) by MAP with priors N(1,0.5), N(0,0.5), N(0,0.5), then freeze. At runtime estimate theta by MAP with N(0,1) prior, subtracting b_j and c_j terms.

**Rationale.** Crowd-BT (Chen et al. 2013) and Dawid-Skene (1979) show reliability-weighted aggregation beats uniform weighting. PoLL (Verga et al. 2024) shows judges differ in agreement with humans. Zheng et al. 2023 and Panickssery et al. 2024 show position and self-preference biases are measurable. A lone agent is one judge with unknown a and uncorrected b, c. No code run.

**Assumptions.** Judge reliability is stable across briefs; At least ~300 past internal votes on externally rated ideas; External reference differs from the evaluation panel

**How it fails.** Noisy a_j estimates add variance; If all judges are equally weak, it reduces to uniform with no gain; Judge model updates invalidate frozen parameters

**Cheapest test.** Offline leave-one-brief-out refit on existing runs: compare pairwise agreement and Kendall tau of theta vs external strengths for {uniform, reliability} weights x {uniform, boundary} allocation at equal votes. Kill if reliability's tau-gain bootstrap interval includes 0.

**Effort.** ~3 days: scoring-module extension and scheduler change. Zero extra tokens at equal budget.

**Operational spec.** judge_model in {uniform, reliability}. Of fixed budget B, 10% uniform across judges (monitoring); 90% to pairs among current top 6 with |theta_i - theta_k| < 0.5, judges sampled proportional to max(a_j,0)^2 (Fisher information per vote), capped at 40% each. Every pair shown in both orders. Refit a, b, c after each benchmark batch.


## Idea Y: Judge-reliability Bradley-Terry fitted to external verdicts

**Pitch.** Weight each finals judge by how well its votes predicted independent raters on past runs, and spend the fixed comparison budget on reliable judges near the top-3 boundary.

**Mechanism.** Judge j is a (model, prompt variant) pair. Vote model: P(i>k | j, i first) = sigmoid(a_j(theta_i - theta_k) + b_j + c_j(f_ij - f_kj)); a_j is discrimination, b_j position bias, f_ij = 1 if idea i's generator shares judge j's family (self-preference). Fit: fix theta of past finalists to external BT strengths, fit (a_j, b_j, c_j) by MAP with priors N(1,0.5), N(0,0.5), N(0,0.5), then freeze. At runtime estimate theta by MAP with N(0,1) prior, subtracting b_j and c_j terms.

**Rationale.** Crowd-BT (Chen et al. 2013) and Dawid-Skene (1979) show reliability-weighted aggregation beats uniform weighting. PoLL (Verga et al. 2024) shows judges differ in agreement with humans. Zheng et al. 2023 and Panickssery et al. 2024 show position and self-preference biases are measurable. A lone agent is one judge with unknown a and uncorrected b, c. No code run (sandbox unavailable).

**Assumptions.** Judge reliability is stable across briefs; At least ~300 past internal votes on externally rated ideas; External reference differs from the evaluation panel

**How it fails.** Noisy a_j estimates add variance; If all judges are equally weak, it reduces to uniform with no gain; Judge model updates invalidate frozen parameters

**Cheapest test.** Offline refit on existing runs: compare held-out-brief pairwise agreement with external rankings and Kendall tau of theta vs external strengths, uniform vs judge-aware BT at equal vote count.

**Effort.** ~3 days: scoring-module extension and scheduler change. Zero extra tokens at equal budget.

**Operational spec.** judge_model in {uniform, reliability}. Of fixed budget B, 10% uniform across judges (monitoring); 90% to pairs among current top 6 with |theta_i - theta_k| < 0.5, judges sampled proportional to max(a_j,0)^2 (Fisher information per vote). Every pair shown in both orders. Refit a, b, c after each benchmark batch.


## Pair p06

## Idea X: Cross-run memory of mutation-operator success, chosen by similarity-weighted Thompson sampling

**Pitch.** Store each parent-versus-child contest as a win or loss for a typed edit operator in the idea library, and in later runs pick operators by Thompson sampling over brief-similar history.

**Mechanism.** The mutator labels each variant with one operator from a fixed taxonomy: narrow scope, swap mechanism, add falsifiable test, graft a rival's strongest component, invert an assumption, cut cost, change target user, quantify the claim. Each contest writes a record (brief embedding, operator, targeted criterion, win/loss, judge model). The run's top 3 are the 'plasma' output; operator statistics are the 'memory'. At mutation time, for the idea's weak criterion, compute alpha=2m+sum(sim*wins) and beta=2(1-m)+sum(sim*losses), m = operator's global win rate, over records with cosine sim>=0.6 and the same criterion, then sample to choose operators.

**Rationale.** Bandit-based adaptive operator selection is established in evolutionary computation (Fialho et al. 2010). PromptBreeder (Fernando et al. 2023) shows evolving mutation instructions helps. The new part is conditioning across runs on brief similarity. Ideas rarely transfer between briefs, but good edit moves may.

**Assumptions.** Operator efficacy generalises across similar briefs; Operator labels are applied faithfully; Card 0's contest loop exists

**How it fails.** Effects too small to detect within a few dozen runs; Memory learns in-loop judge quirks, not quality; Exploitation collapses operator diversity (guard: 1 of 3 slots uniform-random); Stretch transfer: immune memory stores binders, not edit types

**Cheapest test.** Warm the library with 20 training briefs using uniform operators. Run 30 held-out briefs in both arms, memory on versus uniform, at equal cost. Primary: per-brief child-beats-parent rate, paired by brief (contests within a brief are correlated, so per-contest power would overstate). Kill if the paired 95% interval over 30 briefs includes 0. Secondary: benchmark win rate.

**Effort.** 2-3 days on top of card 0; negligible token cost (one embedding per brief).

**Operational spec.** Library table operator_outcomes(run_id, brief_emb, operator, criterion, win, judge). Similarity threshold 0.6; fall back to all records when fewer than 10 match. Thompson draws pick 2 operators, the third is uniform-random. Contest rule as in card 0.


## Idea Y: Cross-run memory of mutation-operator success, chosen by similarity-weighted Thompson sampling

**Pitch.** Store each parent-versus-child contest as a measured win or loss for a typed edit operator in the idea library, and in later runs pick operators by Thompson sampling over brief-similar history.

**Mechanism.** The mutator labels each variant with one operator from a fixed taxonomy: narrow scope, swap mechanism, add falsifiable test, graft a rival's strongest component, invert an assumption, cut cost, change target user, quantify the claim. Each contest writes a record (brief embedding, operator, targeted criterion, win/loss, judge model). The run's top 3 are the 'plasma' output; operator statistics are the 'memory'. At mutation time, for the idea's weak criterion, compute alpha=1+sum(sim*wins) and beta=1+sum(sim*losses) over records with cosine sim>=0.6 and the same criterion, then sample to choose operators.

**Rationale.** Bandit-based adaptive operator selection is established in evolutionary computation (Fialho et al. 2010). PromptBreeder (Fernando et al. 2023) shows evolving mutation instructions helps. The new part is conditioning across runs on brief similarity. Ideas rarely transfer between briefs, but good edit moves may.

**Assumptions.** Operator efficacy generalises across similar briefs; Operator labels are applied faithfully; Card 0's contest loop exists

**How it fails.** Effects too small to detect within a few dozen runs; Memory learns in-loop judge quirks, not quality; Exploitation collapses operator diversity (guard: 1 of 3 slots uniform-random); Stretch transfer: immune memory stores binders, not edit types

**Cheapest test.** Warm the library with 20 training briefs using uniform operators. Run 30 held-out briefs in both arms, memory on versus uniform, at equal cost. Primary measured outcome: child-beats-parent rate (about 540 contests per arm; a 40%-to-50% difference needs about 390 per arm at 80% power, hand-calculated). Secondary: benchmark win rate.

**Effort.** 2-3 days on top of card 0; negligible token cost (one embedding per brief).

**Operational spec.** Library table operator_outcomes(run_id, brief_emb, operator, criterion, win, judge). Similarity threshold 0.6; fall back to all records when fewer than 10 match. Thompson draws pick 2 operators, the third is uniform-random. Contest rule as in card 0.


## Pair p07

## Idea X: Loss-conditioned revision at fixed length with a placebo-calibrated two-family gate

**Pitch.** Revise each finalist from judges' loss reasons at fixed length; accept only if two other-family judges prefer it in both orders, checked against a placebo.

**Mechanism.** Sub-phase after the first pairwise round. (1) Collect up to 5 reasons from each finalist's lost comparisons. (2) The developer fixes only the cited weaknesses, keeping the mechanism, within +/-5% of original tokens (Python check; one retry, else original stays). (3) Gate: two judges of two families outside {generator, developer} compare revised vs original blinded in both orders; accept only on 4/4 wins. (4) Placebo: a same-length no-fix paraphrase takes the gate; its acceptance rate measures style bias. (5) Accepted revisions replace originals in the PL fit; rerun comparisons for changed items only.

**Rationale.** Unverified self-revision often fails (Huang et al. 2023); Self-Refine gains (Madaan et al. 2023) depend on useful feedback, here independent adversaries' reasons. Length matching, both orders, two families and the placebo target verbosity, position and single-judge style bias (Zheng et al. 2023). It changes the delivered text raters read. A lone agent has no independent losses. Cited from memory; web was off; no code run.

**Assumptions.** Stated judge reasons identify real weaknesses; Gate wins beyond placebo rate track rater and outcome preference; A 5% budget leaves room for substantive fixes

**How it fails.** Revisions fix what judges say but cut ambition; Acceptance rate near zero, so no effect; Placebo acceptance above 10%: gate rewards style; swap families or kill

**Cheapest test.** No new generation: saved runs hold finalist cards and loss reasons; revision and gate replay offline on 20 briefs. Primary outcome: the benchmark's own evaluation (measured outcomes, else its blinded panel, outside the gate's families) of delivered top 3 vs the single agent's, at equal judge calls; a no-reasons arm isolates conditioning. Kill if acceptance does not exceed placebo or win rate does not rise.

**Effort.** About 1 week; +30% run cost, less for offline replay.

**Operational spec.** revise(card, loss_reasons[:5], budget=0.95-1.05 x tokens); placebo=paraphrase(card) -> gate(x, original, 2 families not in {gen, dev}, AB+BA) -> accept iff 4/4 -> replace in PL. Arms: unrevised, no-reasons, loss-conditioned.


## Idea Y: Loss-conditioned revision under a fixed card budget with a two-order verifier gate

**Pitch.** Give each finalist's developer the judges' reasons for its losses, allow only a same-length revision, and accept it only if a different-family judge prefers it in both orderings.

**Mechanism.** Development sub-phase after the first pairwise round. (1) Collect up to 5 written reasons from each finalist's lost comparisons. (2) The developer gets the card plus those reasons and must fix only the cited weaknesses, keeping the mechanism, within +/-5% of the original token count (Python check; one retry, else the original stays). (3) A judge from a family different from generator and developer compares revised vs original in both orders, blinded. Accept only if the revision wins both. (4) Accepted revisions replace originals in the PL fit; rerun comparisons for changed items only.

**Rationale.** Unverified self-revision often fails to help (Huang et al. 2023); Self-Refine gains (Madaan et al. 2023) depend on useful feedback. Here the feedback is an independent adversary's reasons, and the gate makes the loop monotone in a verifier's preference. Length matching and both-order acceptance target verbosity and position bias (Zheng et al. 2023). A lone agent has no independent losses to condition on. Cited from memory; web was off.

**Assumptions.** Stated judge reasons identify real weaknesses; The verifier's preference correlates with final raters' preference; A 5% budget leaves room for substantive fixes

**How it fails.** Revisions fix what judges say but cut ambition; Acceptance rate near zero, so no effect; Verifier and final panel share a family, reinforcing its style

**Cheapest test.** On 20 briefs from existing finalist sets, run revise plus gate and report the acceptance rate. A third-family panel rates accepted revisions vs originals, blinded. A control arm revising without loss reasons isolates the value of conditioning.

**Effort.** About 1 week: new sub-phase, length check, verifier prompt, PL replacement handling. Roughly +25% run cost.

**Operational spec.** revise(card, loss_reasons[:5], budget=0.95-1.05 x tokens) -> verify(revised, original, family not in {gen, dev}, orders AB and BA) -> accept iff both wins -> replace in PL. Arms: unrevised, no-reasons revision, loss-conditioned.


## Pair p08

## Idea X: Top-3 chosen as a portfolio by posterior expected maximum with mechanism clusters

**Pitch.** Replace top-3 by score with a set rule maximising the expected best of 3, capped on mean-of-3 loss and identical to top-3 when finalists are diverse.

**Mechanism.** (1) Bootstrap pairwise records (B=2000) and refit BT/PL with a weak ridge prior, giving score samples s_b[i]. (2) One cheap call labels each finalist's mechanism cluster (core lever, not topic; closed list, max 6). (3) Add a shared cluster shift s_b[i] += tau*z_b[c(i)], z ~ N(0,1); tau fitted, not chosen: sd*sqrt(rho/(1-rho)), rho = within-cluster rating correlation on saved runs, floor 0. (4) Greedy: take the top mean, then add items maximising mean_b[max over set of s_b]; ties within 1 SE favour a new cluster. (5) Reject swaps lowering expected mean-of-3 by over 1 SE. If top 3 span 3 clusters or tau = 0, output equals top-3.

**Rationale.** Delivery is exactly what the benchmark judges against a single agent's self-selected 3. A user mostly needs one good idea; best-of-k depends on variance and correlation, not only the mean (Girotra, Terwiesch, Ulrich 2010); top-k ignores correlated duplicates (cf. MMR, Carbonell and Goldstein 1998). A lone agent's own 3 tend to share one theme. Cited from memory; web was off.

**Assumptions.** Same-lever ideas have correlated ratings (fitted on saved data); Cluster labels are consistent; Bootstrap approximates score uncertainty

**How it fails.** Ceiling set by finalist quality (conceded); stacks on quality levers at near-zero cost; Finalists already diverse: identical output, a costless null; Noisy labels make the tie-break random

**Cheapest test.** Offline replay on saved records and ratings: both selections per brief; compare best-of-3 (primary), mean-of-3 (non-inferiority, 1 SE) and win rate vs the single agent's top 3 with a paired bootstrap over briefs. Kill if best-of-3 does not rise on briefs where selections differ.

**Effort.** 2-3 days: about 60 lines of NumPy, one prompt, one config flag.

**Operational spec.** select_top3(records, labels, B=2000, tau=fit(saved_runs), k=3, tie_se=1.0, max_mean_drop_se=1.0). Flag portfolio_select on/off. Metrics: best-of-3, mean-of-3, win rate vs single agent.


## Idea Y: Top-3 chosen as a portfolio by posterior expected maximum with mechanism clusters

**Pitch.** Replace 'take the 3 highest Bradley-Terry scores' with a set-selection rule that maximises the expected best idea among the delivered 3.

**Mechanism.** Scoring-module change only. (1) Bootstrap the pairwise records B=2000 times and refit BT/PL with a weak ridge prior to get score samples s_b[i]. (2) One cheap call labels each finalist with a mechanism cluster (the core lever pulled, not the topic), from a closed list of at most 6. (3) Add a shared cluster shift s_b[i] += tau*z_b[c(i)], z ~ N(0,1), tau = 0.5 x pooled score SD, so same-lever ideas succeed or fail together. (4) Greedy: take the highest mean score, then repeatedly add the item maximising mean_b[max over set of s_b]; ties within 1 SE go to a new cluster.

**Rationale.** A user mostly needs one good idea, and best-of-k value depends on variance and correlation, not only the mean (Girotra, Terwiesch, Ulrich 2010). Top-k by score ignores correlated duplicates; MMR reranking (Carbonell and Goldstein 1998) targets the same problem. A single agent picking 3 of its own 20 tends to choose variants of its favourite theme and has no posterior. Cited from memory; web was off.

**Assumptions.** Same-lever ideas have positively correlated ratings (checkable on existing data); Cluster labels are consistent; The comparison bootstrap approximates real score uncertainty

**How it fails.** If the metric is mean rating of the top 3, diversification loses by construction; make best-of-3 primary; Finalists already diverse, so a null result; Noisy labels make the tie-break random

**Cheapest test.** Offline replay on saved pairwise records and panel ratings: compute both selections per brief, compare best-of-3, mean-of-3 and distinct clusters with a paired bootstrap over briefs. Cost: one labelling call per brief.

**Effort.** 2-3 days: about 60 lines of NumPy, one prompt, one config flag.

**Operational spec.** select_top3(records, labels, B=2000, tau=0.5*sd_pooled, k=3, tie_se=1.0). Flag portfolio_select on/off. Metrics: best-of-3 rating, mean-of-3, distinct clusters.


## Pair p09

## Idea X: Boundary-targeted help budget with survivor-mutation cycles

**Pitch.** Spend critique and mutation calls only on ideas straddling the top-3 cutoff, and re-enter their single-edit mutants for up to 3 cycles, accepted by judges that never ranked them.

**Mechanism.** New phase MATURE between critique and finals. Round 0: order-swapped pairwise judging against the frozen brief-plus-rubric; fit Bradley-Terry; bootstrap rank intervals. Up to H=6 ideas straddling rank 3/4 each get one critique naming their weakest criterion, then one mutator call writing k=3 same-length single-edit variants. Gate judges, a family B that is neither the ranker's nor the benchmark panel's, see only length-normalised claim, mechanism and test fields. Accepted variants replace parents; refit and repeat.

**Rationale.** Top-k identification bandits (LUCB; Kalyanakrishnan et al. 2012) need far fewer samples when effort concentrates near the cutoff. A lone agent lacks an independent signal: models favour their own outputs (Panickssery et al. 2024) and self-correct poorly (Huang et al. 2023). No code run.

**Assumptions.** Gate-family preferences track the independent panel's; Single targeted edits help more often than they harm; Some ideas sit near the cutoff

**How it fails.** Mutants still overfit LLM judges generally; the gate bounds this and the overfit gap measures it; Sparse round-0 data widens intervals, so H does the selecting; Partial transfer: germinal centres favour top clones (Gitlin et al. 2014), not boundary ones; Mutants converge to near-duplicates

**Cheapest test.** 10 briefs, equal tokens: MATURE versus uniform development of the point-estimate top 6. Primary: blinded, counterbalanced benchmark win rate against the single agent's top 3. Secondary: child-beats-parent rate under a held-out family; overfit gap is the gate-family minus held-out rate. Kill: held-out rate ≤50% or gap >15 points.

**Effort.** 3-5 days; per cycle about 6 critiques, 6 mutator calls, 72 judge calls; +30-50% run cost.

**Operational spec.** Round 0: 3 comparisons per idea, both orders. BT module, 200 bootstrap resamples, 10th-90th percentile rank interval. Boundary: lo<=3 and hi>=4; keep 6 with P(top3) nearest 0.5. Accept iff, under family B, the variant wins both orderings against its parent and one against the rank-3 incumbent, within 10% of parent length. Max 3 cycles; stop when the boundary set is unchanged.


## Idea Y: Boundary-targeted help budget with survivor-mutation cycles

**Pitch.** Spend critique and mutation calls only on ideas whose rank interval straddles the top-3 cutoff, and re-enter their single-edit mutants for up to 3 cycles.

**Mechanism.** New phase MATURE between critique and finals. Round 0: order-swapped pairwise judging against the frozen brief-plus-rubric; fit Bradley-Terry; bootstrap rank intervals. Up to H=6 ideas straddling rank 3/4 each get one critique naming their weakest criterion, then one mutator call writing k=3 same-length single-edit variants. A variant replaces its parent only if it beats the parent and the rank-3 incumbent. Refit and repeat.

**Rationale.** Top-k identification bandits (LUCB; Kalyanakrishnan et al. 2012) need far fewer samples when effort concentrates near the cutoff; MATURE concentrates refinement the same way. A lone agent lacks an independent signal: models favour their own outputs (Panickssery et al. 2024) and self-correct poorly without external feedback (Huang et al. 2023). No code was run.

**Assumptions.** In-loop judge preferences track the independent panel's; Single targeted edits help more often than they harm; Some ideas sit near the cutoff

**How it fails.** Mutants overfit the in-loop judge; mitigate with a judge family different from the panel and a 10% length cap; Sparse round-0 data widens every interval, so H does all the selecting; Partial transfer: real germinal centres give most help to top clones (Gitlin et al. 2014), not boundary ones; Mutants converge to near-duplicates

**Cheapest test.** 10 briefs, equal tokens: MATURE versus uniform development of the point-estimate top 6. Primary: blinded, counterbalanced benchmark win rate against the single agent's top 3. Secondary: child-beats-parent rate under a held-out judge family.

**Effort.** 3-5 days; per cycle about 6 critiques, 6 mutator calls and 72 short judge calls; roughly +30-50% run cost.

**Operational spec.** Round 0: 3 comparisons per idea, both orders. Existing BT module, 200 bootstrap resamples, 10th-90th percentile rank interval. Boundary: lo<=3 and hi>=4; keep 6 with P(top3) nearest 0.5. Accept a variant iff it wins both orderings against its parent and one against the rank-3 incumbent. Max 3 cycles; stop when the boundary set is unchanged.


## Pair p10

## Idea X: Residual selection head learned from the library's blinded verdicts

**Pitch.** Replace the final top-3 cut with a regularised within-run logistic model, trained on blinded verdicts from a non-panel rater, that first only penalises nuisance-feature bias.

**Mechanism.** Per finalist the library stores internal BT strength, critic scores, generator id, library similarity, and nuisance covariates (word count, citation/hedge counts, judge-generator family match). Label: fraction of counterbalanced external comparisons won against the baseline's three cards. Conditional logit within each run cancels brief effects: logit p = beta0*BT + w.x, beta0 fixed, w ~ N(0, sigma^2). Stage 1 (about 5 briefs): only nuisance weights are free, constrained w<=0, so it can only penalise length or polish. Stage 2 (about 15 briefs): content weights unlock if leave-one-brief-out gain holds.

**Rationale.** Length-controlled AlpacaEval (Dubois et al. 2024) regresses out length; this applies that to selection. Zheng et al. 2023 and Panickssery et al. 2024 document the biases the covariates target. Si et al. 2024 found LLM idea rankings agree weakly with experts. A lone agent never sees its selection error. No code run.

**Assumptions.** Stage 1 needs about 5 labelled briefs; Selection error is partly systematic across briefs; Labellers are humans or a family outside the eval panel and loop

**How it fails.** Labels teach the labeller's biases (Goodhart); an audit panel measures this; Stage 2 may fit noise at ~10 rows per brief and stays off; Generator changes shift the distribution; Conceded: only reorders the pool; ceiling is pool quality

**Cheapest test.** Offline, no new generation: label all finalists once with a non-panel family. Compare leave-one-brief-out AUC and top-3 win rate, stage 1 versus internal BT, on an audit panel. Kill if oracle headroom (top-3 by labels versus internal BT) is under 5 win-rate points, or stage 1 shows no gain.

**Effort.** ~4 days: schema, labelling job, ~80-line NumPy IRLS fit, switch; run cost unchanged.

**Operational spec.** select_by in {internal_BT, calibrated}. Binomial log-likelihood on (wins, trials), L2 lambda=1 on w, per-run z-scored features; label weight 3 for human/measured, 1 for model rater. Nuisance weights sign-constrained (w<=0) and kept at selection. Fall back to internal_BT below 5 labelled briefs. Evaluate by leave-one-brief-out log-loss/AUC, then top-3 win rate with an audit panel.


## Idea Y: Residual selection head learned from the library's blinded verdicts

**Pitch.** Replace the final top-3 cut with a regularised logistic model, trained on past blinded benchmark verdicts, that predicts which finalists beat the baseline.

**Mechanism.** The library stores per finalist x: internal BT strength (z-scored per run), per-criterion critic scores, development score delta, generator id, max cosine similarity to library ideas, and nuisance covariates (word count, citation/hedge counts, judge-generator family match). Label: fraction of counterbalanced external comparisons it wins against the baseline's three cards. Residual model: logit p = beta0*BT + w.x, beta0 fixed at the current internal weight, w ~ N(0, sigma^2), so with few labels it reduces to today's ranking.

**Rationale.** Length-controlled AlpacaEval (Dubois et al. 2024) regresses preferences on length and zeroes that term, removing much verbosity bias; this applies it to selection. Zheng et al. 2023 and Panickssery et al. 2024 document the verbosity, position and self-preference biases the covariates target. Si et al. 2024 found LLM idea rankings agree weakly with experts, so internal ranking error exists to learn. A lone agent never sees its own selection error. No code run (sandbox unavailable).

**Assumptions.** At least ~15 benchmarked briefs with all finalists labelled; Selection error is partly systematic across briefs; Training labels come from humans or a model family different from the eval panel

**How it fails.** Labels from the eval panel teach its biases (Goodhart); Brief heterogeneity swamps ~10 labels per brief; Generator changes shift the distribution

**Cheapest test.** Offline on existing runs: panel-rate all finalists once (~10 x 3 baseline cards x 2 orders). Compare leave-one-brief-out AUC and top-3 win rate, calibrated vs internal BT. No new generation.

**Effort.** ~4 days: schema, labelling job, ~80-line NumPy IRLS fit, switch. Benchmark panel cost doubles once; run cost unchanged.

**Operational spec.** select_by in {internal_BT, calibrated}. Binomial log-likelihood on (wins, trials), L2 lambda=1 on w, per-run z-scored features; label weight 3 for human/measured, 1 for panel. At selection, zero nuisance terms so they absorb bias without being rewarded. Fall back to internal_BT below 15 labelled briefs. Evaluate by leave-one-brief-out log-loss/AUC, then top-3 win rate on later briefs with a different-family panel.


## Pair p11

## Idea X: Judge-reliability Bradley-Terry fitted to external verdicts

**Pitch.** Weight finals judges by agreement with independent raters, remove position, self-preference and shared verbosity biases, and focus the budget on reliable judges near the top-3 boundary.

**Mechanism.** Judge j = (model, prompt variant). Vote: P(i>k | j, i first) = sigmoid(a_j(theta_i - theta_k) + b_j + c_j(f_ij - f_kj) + g.(z_i - z_k)). f_ij = 1 if i's generator shares j's family; z = z-scored length, hedges, formatting; g is shared across judges, so bias common to all is absorbed, not rewarded. a_j shrinks to a common a, b_j and c_j to 0: with scarce data this is uniform BT plus bias correction. Label-free calibration: b_j from order swaps, c_j from authorship-relabelled duplicates, g from length-inflated paraphrase pairs; only a_j needs external verdicts.

**Rationale.** Crowd-BT (Chen et al. 2013) shows reliability-weighted aggregation beats uniform weighting. Zheng et al. 2023 and Panickssery et al. 2024 show position and self-preference biases are measurable. A lone agent is one judge with unknown a and uncorrected b, c, g. No code run.

**Assumptions.** Bias terms are stable across briefs; About 100 external votes fit a_j; External reference differs from the evaluation panel

**How it fails.** Noisy a_j adds variance; shrinkage bounds it; If judges are equally reliable, only bias terms help, possibly little; Probe effects may differ from real cards

**Cheapest test.** Step 1, no external labels: run probes; report b, c, g and whether g excludes 0. Step 2, offline on existing runs: held-out-brief Kendall tau against external strengths for uniform, bias-only and full BT at equal votes. Kill if both gain under 0.03 tau.

**Effort.** ~3-4 days: scoring extension, probe generator, scheduler; ~1000 extra short judge calls once.

**Operational spec.** judge_model in {uniform, bias_only, reliability}. Of fixed budget B, 10% uniform across judges; 90% to pairs among current top 6 with |theta_i - theta_k| < 0.5, judges sampled proportional to max(a_j,0)^2. Both orders. Fit a_j by MAP (prior N(1,0.5)) on external strengths, freeze; theta by MAP (N(0,1)). Judge updates invalidate parameters; rerun probes.


## Idea Y: Judge-reliability Bradley-Terry fitted to external verdicts

**Pitch.** Weight each finals judge by how well its votes predicted independent raters on past runs, and spend the fixed comparison budget on reliable judges near the top-3 boundary.

**Mechanism.** Judge j is a (model, prompt variant) pair. Vote model: P(i>k | j, i first) = sigmoid(a_j(theta_i - theta_k) + b_j + c_j(f_ij - f_kj)); a_j is discrimination, b_j position bias, f_ij = 1 if idea i's generator shares judge j's family (self-preference). Fit: fix theta of past finalists to external BT strengths, fit (a_j, b_j, c_j) by MAP with priors N(1,0.5), N(0,0.5), N(0,0.5), then freeze. At runtime estimate theta by MAP with N(0,1) prior, subtracting b_j and c_j terms.

**Rationale.** Crowd-BT (Chen et al. 2013) and Dawid-Skene (1979) show reliability-weighted aggregation beats uniform weighting. PoLL (Verga et al. 2024) shows judges differ in agreement with humans. Zheng et al. 2023 and Panickssery et al. 2024 show position and self-preference biases are measurable. A lone agent is one judge with unknown a and uncorrected b, c. No code run (sandbox unavailable).

**Assumptions.** Judge reliability is stable across briefs; At least ~300 past internal votes on externally rated ideas; External reference differs from the evaluation panel

**How it fails.** Noisy a_j estimates add variance; If all judges are equally weak, it reduces to uniform with no gain; Judge model updates invalidate frozen parameters

**Cheapest test.** Offline refit on existing runs: compare held-out-brief pairwise agreement with external rankings and Kendall tau of theta vs external strengths, uniform vs judge-aware BT at equal vote count.

**Effort.** ~3 days: scoring-module extension and scheduler change. Zero extra tokens at equal budget.

**Operational spec.** judge_model in {uniform, reliability}. Of fixed budget B, 10% uniform across judges (monitoring); 90% to pairs among current top 6 with |theta_i - theta_k| < 0.5, judges sampled proportional to max(a_j,0)^2 (Fisher information per vote). Every pair shown in both orders. Refit a, b, c after each benchmark batch.


## Pair p12

## Idea X: Cross-run memory of mutation-operator success, chosen by similarity-weighted Thompson sampling

**Pitch.** Record each parent-versus-child contest as a measured win or loss for a typed edit operator, warm-start offline on saved ideas, and pick operators by Thompson sampling over brief-similar history.

**Mechanism.** Each variant carries one operator: narrow scope, swap mechanism, add falsifiable test, graft a rival's strongest component, invert an assumption, cut cost, change target user, quantify the claim. A child wins only if it beats its parent in both orders under a non-mutator judge family, within 10% of the parent's length. Each contest writes (brief embedding, operator, criterion, win/loss, judge family). Warm start: 8 operators x ~100 saved finalists (~800 contests), no new runs. For the idea's weak criterion, alpha=1+sum(sim*wins) and beta=1+sum(sim*losses) over records with cosine sim>=0.6 and that criterion; sample.

**Rationale.** Bandit-based adaptive operator selection is established in evolutionary computation (Fialho et al. 2010); PromptBreeder (Fernando et al. 2023) evolves mutation instructions. New here: conditioning on brief similarity across runs. Ideas rarely transfer across briefs; edit moves may. No code run.

**Assumptions.** Operator win rates differ beyond noise; Efficacy generalises across similar briefs; Operator labels are applied faithfully

**How it fails.** Effect small: it only tunes which edit is tried (conceded); Memory learns gate-judge quirks; family split, length cap and audit limit this; Exploitation collapses diversity (guard: 1 of 3 slots random); Stretch transfer: immune memory stores binders, not edits

**Cheapest test.** Stage 1, offline on warm-start contests: chi-square that operator win rates differ; leave-one-brief-out log-loss of similarity-weighted versus pooled rates. Kill if p>0.1 or no gain. Stage 2: 30 held-out briefs, memory versus uniform at equal cost; primary child-beats-parent rate under an audit family (40%-to-50% needs about 390 contests per arm at 80% power, hand-calculated); secondary benchmark win rate.

**Effort.** 2-3 days: contest loop (~40 lines), operator table, ~1600 warm-start judge calls; negligible per-run tokens.

**Operational spec.** Table operator_outcomes(run_id, brief_emb, operator, criterion, win, judge). Similarity threshold 0.6; below 10 matches, use pooled records. Thompson draws pick 2 operators, the third is uniform-random.


## Idea Y: Cross-run memory of mutation-operator success, chosen by similarity-weighted Thompson sampling

**Pitch.** Store each parent-versus-child contest as a measured win or loss for a typed edit operator in the idea library, and in later runs pick operators by Thompson sampling over brief-similar history.

**Mechanism.** The mutator labels each variant with one operator from a fixed taxonomy: narrow scope, swap mechanism, add falsifiable test, graft a rival's strongest component, invert an assumption, cut cost, change target user, quantify the claim. Each contest writes a record (brief embedding, operator, targeted criterion, win/loss, judge model). The run's top 3 are the 'plasma' output; operator statistics are the 'memory'. At mutation time, for the idea's weak criterion, compute alpha=1+sum(sim*wins) and beta=1+sum(sim*losses) over records with cosine sim>=0.6 and the same criterion, then sample to choose operators.

**Rationale.** Bandit-based adaptive operator selection is established in evolutionary computation (Fialho et al. 2010). PromptBreeder (Fernando et al. 2023) shows evolving mutation instructions helps. The new part is conditioning across runs on brief similarity. Ideas rarely transfer between briefs, but good edit moves may.

**Assumptions.** Operator efficacy generalises across similar briefs; Operator labels are applied faithfully; Card 0's contest loop exists

**How it fails.** Effects too small to detect within a few dozen runs; Memory learns in-loop judge quirks, not quality; Exploitation collapses operator diversity (guard: 1 of 3 slots uniform-random); Stretch transfer: immune memory stores binders, not edit types

**Cheapest test.** Warm the library with 20 training briefs using uniform operators. Run 30 held-out briefs in both arms, memory on versus uniform, at equal cost. Primary measured outcome: child-beats-parent rate (about 540 contests per arm; a 40%-to-50% difference needs about 390 per arm at 80% power, hand-calculated). Secondary: benchmark win rate.

**Effort.** 2-3 days on top of card 0; negligible token cost (one embedding per brief).

**Operational spec.** Library table operator_outcomes(run_id, brief_emb, operator, criterion, win, judge). Similarity threshold 0.6; fall back to all records when fewer than 10 match. Thompson draws pick 2 operators, the third is uniform-random. Contest rule as in card 0.


## Output

Write one JSON object to `/home/user/agent-brainswarm/benchmark/experiments/loss-revision/out/gate-fable-1.json`: {"verdicts": [{"pair": "p01", "winner": "X or Y", "reason": "one sentence"}]}, one verdict per pair.
