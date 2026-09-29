# Idea revision task

You revise idea cards for a system that generates ideas for the brief below. Read no file other than this one.

## Brief

Ways to make a multi-agent idea-generation system (independent generators, justified critique, development of selected ideas, LLM-judged pairwise finals) produce top ideas that measured outcomes or independent raters prefer over a single strong agent's self-selected top 3 for the same brief. Hard rules: each change must be implementable in this codebase and testable with the existing benchmark.

## Idea I004

```json
{
 "title": "Loss-conditioned revision under a fixed card budget with a two-order verifier gate",
 "pitch": "Give each finalist's developer the judges' reasons for its losses, allow only a same-length revision, and accept it only if a different-family judge prefers it in both orderings.",
 "mechanism": "Development sub-phase after the first pairwise round. (1) Collect up to 5 written reasons from each finalist's lost comparisons. (2) The developer gets the card plus those reasons and must fix only the cited weaknesses, keeping the mechanism, within +/-5% of the original token count (Python check; one retry, else the original stays). (3) A judge from a family different from generator and developer compares revised vs original in both orders, blinded. Accept only if the revision wins both. (4) Accepted revisions replace originals in the PL fit; rerun comparisons for changed items only.",
 "rationale": "Unverified self-revision often fails to help (Huang et al. 2023); Self-Refine gains (Madaan et al. 2023) depend on useful feedback. Here the feedback is an independent adversary's reasons, and the gate makes the loop monotone in a verifier's preference. Length matching and both-order acceptance target verbosity and position bias (Zheng et al. 2023). A lone agent has no independent losses to condition on. Cited from memory; web was off.",
 "assumptions": [
  "Stated judge reasons identify real weaknesses",
  "The verifier's preference correlates with final raters' preference",
  "A 5% budget leaves room for substantive fixes"
 ],
 "failure_modes": [
  "Revisions fix what judges say but cut ambition",
  "Acceptance rate near zero, so no effect",
  "Verifier and final panel share a family, reinforcing its style"
 ],
 "cheapest_test": "On 20 briefs from existing finalist sets, run revise plus gate and report the acceptance rate. A third-family panel rates accepted revisions vs originals, blinded. A control arm revising without loss reasons isolates the value of conditioning.",
 "effort": "About 1 week: new sub-phase, length check, verifier prompt, PL replacement handling. Roughly +25% run cost.",
 "spec": "revise(card, loss_reasons[:5], budget=0.95-1.05 x tokens) -> verify(revised, original, family not in {gen, dev}, orders AB and BA) -> accept iff both wins -> replace in PL. Arms: unrevised, no-reasons revision, loss-conditioned."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I008 can be switched on and off by offline refits on saved runs and scored by held-out agreement with external rankings (Kendall tau) at equal vote count. I004 needs new runs and shows its effect mainly through panel opinion.
- I008 explicitly models and subtracts position and same-family bias, anchored to external verdicts. I004's acceptance gate still rests on one LLM judge's preference, so its gains may reflect that judge's style.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 366 words in total (the original has 349).

## Idea I003

```json
{
 "title": "Top-3 chosen as a portfolio by posterior expected maximum with mechanism clusters",
 "pitch": "Replace 'take the 3 highest Bradley-Terry scores' with a set-selection rule that maximises the expected best idea among the delivered 3.",
 "mechanism": "Scoring-module change only. (1) Bootstrap the pairwise records B=2000 times and refit BT/PL with a weak ridge prior to get score samples s_b[i]. (2) One cheap call labels each finalist with a mechanism cluster (the core lever pulled, not the topic), from a closed list of at most 6. (3) Add a shared cluster shift s_b[i] += tau*z_b[c(i)], z ~ N(0,1), tau = 0.5 x pooled score SD, so same-lever ideas succeed or fail together. (4) Greedy: take the highest mean score, then repeatedly add the item maximising mean_b[max over set of s_b]; ties within 1 SE go to a new cluster.",
 "rationale": "A user mostly needs one good idea, and best-of-k value depends on variance and correlation, not only the mean (Girotra, Terwiesch, Ulrich 2010). Top-k by score ignores correlated duplicates; MMR reranking (Carbonell and Goldstein 1998) targets the same problem. A single agent picking 3 of its own 20 tends to choose variants of its favourite theme and has no posterior. Cited from memory; web was off.",
 "assumptions": [
  "Same-lever ideas have positively correlated ratings (checkable on existing data)",
  "Cluster labels are consistent",
  "The comparison bootstrap approximates real score uncertainty"
 ],
 "failure_modes": [
  "If the metric is mean rating of the top 3, diversification loses by construction; make best-of-3 primary",
  "Finalists already diverse, so a null result",
  "Noisy labels make the tie-break random"
 ],
 "cheapest_test": "Offline replay on saved pairwise records and panel ratings: compute both selections per brief, compare best-of-3, mean-of-3 and distinct clusters with a paired bootstrap over briefs. Cost: one labelling call per brief.",
 "effort": "2-3 days: about 60 lines of NumPy, one prompt, one config flag.",
 "spec": "select_top3(records, labels, B=2000, tau=0.5*sd_pooled, k=3, tie_se=1.0). Flag portfolio_select on/off. Metrics: best-of-3 rating, mean-of-3, distinct clusters."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I003 only reshuffles already-scored finalists and by construction can lose on mean-of-3, with a cluster-correlation tau chosen ad hoc. I004 raises the quality of the finalists themselves through independent loss feedback under a bias-controlled acceptance gate.
- I004 improves the substance of the delivered ideas through independent loss-conditioned revision. I003 only reorders an existing finalist set, so its gain disappears if finalists are already diverse, and it can lower mean-of-3 by construction.
- I001 can raise the quality of the delivered ideas through an independent-signal refinement loop, while I003 only re-selects among existing finalists and risks a null result or a loss on mean rating.
- I001 can raise the quality of the ideas through targeted refinement guided by an independent judge, a larger potential gain than I003, which only reshuffles a fixed finalist pool and can lose on mean rating or have no effect if the finalists are already diverse.
- I003 only reorders finalists that already exist, so its ceiling is set by their quality. It admits it loses by construction if the benchmark scores the mean of the top 3, and it may give a null result if the finalists are already diverse. I006 raises the substance of the delivered ideas by removing claims that fail a check, which is a gain raters without LLM-judge biases should also prefer.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 342 words in total (the original has 326).

## Idea I005

```json
{
 "title": "Claim ledger with executable checks; survival scored on checks passed",
 "pitch": "Falsifiable claims replace prose critique; sandbox runs and library lookups decide them, so ideas advance on checks passed, not eloquence.",
 "mechanism": "New phase `claim_extraction` before critique: an extractor role (different model family) rewrites each sketch into 4-8 typed claims, each with a tolerance. Every critic objection must carry exactly one artifact: (a) a sandbox script that consumes the claim's numbers and prints PASS/FAIL; (b) a library lookup of past ideas at cosine >= 0.85 with recorded outcomes and falsifications (a novelty claim FAILs on a falsified hit); or (c) `not_checkable`, weight 0. The state machine runs artifacts; errors or timeouts = INCONCLUSIVE. Score s = P - 2F (P passed, F falsified) ranks ideas into development. The selector sees only the ledger, never critic prose. Cards with under 3 checkable claims rank last.",
 "rationale": "Self-critique without external signal does not improve LLM reasoning (Huang 2023); tool-grounded critique does (Gou 2023). Atomic-claim decomposition makes verification more reliable (Min 2023). Persuasive prose sways judges independently of truth (Khan 2024; Zheng 2023); withholding it closes that channel. A single agent has no cross-run outcome library and does not falsify its own claims. Stage: critique and selection.",
 "assumptions": [
  "About 40% of claims are checkable by a 30 s numpy script or a lookup.",
  "Falsified-claim rate in a top-3 tracks rater or outcome preference."
 ],
 "failure_modes": [
  "Rigged checks (unconditional FAIL); mitigated by the consume-the-numbers rule and a 10% third-family audit.",
  "Qualitative briefs yield mostly `not_checkable`; s ~ 0 discriminates nothing.",
  "Generators hedge claims into unfalsifiable form; the 3-claim floor only partly blocks this."
 ],
 "cheapest_test": "One brief, critique run twice at equal tokens: prose-only (off) vs ledger (on). A held-out model family re-runs extractor plus checker over both top-3s and the single agent's top 3; report falsified-claim rate and blinded panel ranking. No sandbox code was run.",
 "effort": "One week; critique-phase tokens +30-50%.",
 "spec": "Script: last stdout line PASS|FAIL, 30 s, numpy/scipy, no network. Lookup: cosine >= 0.85, k = 5. s = P - 2F; min-checkable 3; tie-break BT. Off-switch `critique.mode = prose|ledger`, equal tokens."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I005 concedes that qualitative briefs yield mostly not_checkable claims so s is near zero and discriminates nothing (and its 3-claim floor then ranks good but unquantifiable ideas last), while I001's boundary refinement applies to every kind of brief.
- I005's own failure analysis concedes that qualitative briefs (including briefs like this one) yield mostly not_checkable claims and s ~ 0 discriminates nothing, and its ~40%-checkable assumption is untested with 6 major critiques open, whereas I001's mechanism works on every kind of brief.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 374 words in total (the original has 357).

## Idea I006

```json
{
 "title": "Check-repair development loop with a cross-run library of check templates",
 "pitch": "A bounded repair loop sees only failed checks and must pass or strike them; every executed check becomes a reusable cross-run template.",
 "mechanism": "Repair loop, at most 3 iterations. The developer receives ledger rows with outcome FAIL or INCONCLUSIVE, plus check output, no critic prose. Options per row: (1) revise the idea until the same check passes on re-execution; (2) strike the claim; (3) contest with a counter-check, adjudicated by a third-model-family role that picks the check faithful to the claim's wording, else INCONCLUSIVE. After iteration 3 every non-PASS claim is struck. Each executed check is stored in the idea library as a parameterised template; prompts authoring a check are prepended with the top-3 templates at cosine > 0.8, to parameterise rather than rewrite. Final cards show no badges or check text.",
 "rationale": "Code self-repair improves with execution feedback (Chen 2023) but the gain is bounded by feedback quality (Olausson 2023), motivating the 3-iteration cap and concrete check outcomes instead of prose. Voyager (Wang 2023) shows an accumulating library of verified executable skills lets later episodes reuse rather than re-improvise. A single agent has no prior runs to borrow checks from. Stage: development, compounding across runs.",
 "assumptions": [
  "Card 0's ledger or an equivalent set of executable checks exists at development time.",
  "Claim patterns recur across briefs enough for templates to be reused."
 ],
 "failure_modes": [
  "Developers weaken claims to triviality; diagnostic: claims per final card and rater specificity scores.",
  "A wrong template propagates across runs; mitigated by dropping templates with adjudicator-contested rate above 30%."
 ],
 "cheapest_test": "Same brief, development run twice at equal tokens: one-shot (off) vs repair loop (on). Outcomes: falsified-claim rate of the top 3 under a held-out checker of another model family; claims struck per idea; template reuse rate on a second brief. No sandbox code was run.",
 "effort": "One to two weeks; development tokens roughly 2x.",
 "spec": "for it in 1..3: rows = ledger.where(outcome in {FAIL, INCONCLUSIVE}); developer(rows, templates) -> revise | strike | contest; re-execute; contested -> adjudicator. Retrieval: cosine > 0.8, k = 3, exclude contested_rate > 0.3. Flags: `develop.mode = oneshot|repair`, `develop.max_iter = 3`, `templates.enabled` isolates library from loop."
}
```

Judges' reasons for each comparison this idea lost in the finals:
- I006 assumes the whole I005 claim-ledger infrastructure already exists, roughly doubles development tokens and carries 7 open major critiques. I004 is a self-contained one-week sub-phase at about +25% cost.
- I006 is built on top of I005's ledger, so it cannot be tested without it. It also costs about twice the development tokens and has more open major critiques, while I005 is the cheaper prerequisite at +30-50% critique tokens.
- I006 depends on I005's ledger already existing, roughly doubles development tokens and has 7 open major critiques. I005 is the self-contained foundation, buildable in about a week at +30-50% critique tokens.
- I004 can be built in about a week at about +25% run cost without prerequisites. I006 needs a claim-ledger infrastructure that does not yet exist, costs about 2x development tokens and carries many unresolved major critiques, including developers weakening claims to trivial ones.
- I003 needs 2-3 days, about 60 lines and almost no extra tokens, and its test is an offline replay. I006 needs one to two weeks, roughly doubles development tokens, has 7 open major critiques, and depends on an unverified assumption that executable check ledgers exist at development time.
- I008 directly models and removes position and self-preference bias and is validated against external rankings at no extra token cost, whereas I006 costs about 2x, depends on an unconfirmed check ledger, risks trivially weakened claims, and its final cards show no check text, so the gain may not reach the raters.

Revise the card to address these reasons. It must stay the same idea. The revised card may have at most 389 words in total (the original has 371).

## Output

Write one JSON object to `/home/user/agent-brainswarm/benchmark/experiments/loss-revision/out/treatment-opus.json`: {"revisions": {"<idea id>": {<the card fields: title, pitch, mechanism, rationale, assumptions (list), failure_modes (list), cheapest_test, effort, spec>}}}, with one entry for every idea above.
