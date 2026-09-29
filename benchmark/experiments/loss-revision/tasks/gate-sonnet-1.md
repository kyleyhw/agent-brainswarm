# Pairwise judgement task

For each pair, decide which version of the idea you would rather pursue for the brief below. Judge substance, not length or polish; the order carries no information. Read no file other than this one.

## Brief

Ways to make a multi-agent idea-generation system (independent generators, justified critique, development of selected ideas, LLM-judged pairwise finals) produce top ideas that measured outcomes or independent raters prefer over a single strong agent's self-selected top 3 for the same brief. Hard rules: each change must be implementable in this codebase and testable with the existing benchmark.

## Pair p01

## Idea X: Claim ledger with executable checks; survival scored on checks passed

**Pitch.** Falsifiable claims replace prose critique; sandbox runs and library lookups decide them, so ideas advance on checks passed, not eloquence.

**Mechanism.** New phase `claim_extraction` before critique: an extractor role (different model family) rewrites each sketch into 4-8 typed claims, each with a tolerance and a load-bearing flag. Each objection carries one artifact: (a) a sandbox script consuming the claim's numbers, printing PASS/FAIL, plus a witness value that flips it; (b) a lookup of library ideas at cosine >= 0.85 (a novelty claim FAILs on a falsified hit); or (c) `not_checkable`, weight 0. The state machine runs scripts at claimed and witness values; no flip, error or timeout = INCONCLUSIVE. Score s = (P - 2F)/max(3, n) over checkable load-bearing claims ranks ideas into development. The selector sees only the ledger, never critic prose. Cards with under 3 checkable claims rank last.

**Rationale.** Self-critique without external signal does not improve LLM reasoning (Huang 2023); tool-grounded critique does (Gou 2023). Persuasive prose sways judges independently of truth (Khan 2024; Zheng 2023); withholding it closes that channel. A single agent has no cross-run outcome library and does not falsify its own claims.

**Assumptions.** About 40% of claims are checkable by a 30 s numpy script or a lookup.; Falsified-claim rate in a top-3 tracks rater or outcome preference.

**How it fails.** Rigged checks (unconditional FAIL); blocked by the witness flip, plus a 10% third-family audit.; Qualitative briefs yield mostly `not_checkable`; s ~ 0 discriminates nothing.; Generators hedge claims into unfalsifiable form; the 3-claim floor only partly blocks this.; Favours safe, modest ideas; ambition is a guard metric.

**Cheapest test.** 10 briefs, critique run twice at equal tokens: prose-only (off) vs ledger (on). Primary: blinded held-out-family panel ranks each arm's top 3 against the single agent's. Secondary: held-out falsified-claim rate. Kill if ledger beats prose under 55%, ambition falls over 0.5/5, or checkable claims are under 25%. No sandbox code was run.

**Effort.** One week; critique-phase tokens +30-50%.

**Operational spec.** Script: last stdout line PASS|FAIL, 30 s, numpy/scipy, no network. Lookup: cosine >= 0.85, k = 5. min-checkable 3; tie-break BT. Off-switch `critique.mode = prose|ledger`, equal tokens.


## Idea Y: Claim ledger with executable checks; survival scored on checks passed

**Pitch.** Falsifiable claims replace prose critique; sandbox runs and library lookups decide them, so ideas advance on checks passed, not eloquence.

**Mechanism.** New phase `claim_extraction` before critique: an extractor role (different model family) rewrites each sketch into 4-8 typed claims, each with a tolerance. Every critic objection must carry exactly one artifact: (a) a sandbox script that consumes the claim's numbers and prints PASS/FAIL; (b) a library lookup of past ideas at cosine >= 0.85 with recorded outcomes and falsifications (a novelty claim FAILs on a falsified hit); or (c) `not_checkable`, weight 0. The state machine runs artifacts; errors or timeouts = INCONCLUSIVE. Score s = P - 2F (P passed, F falsified) ranks ideas into development. The selector sees only the ledger, never critic prose. Cards with under 3 checkable claims rank last.

**Rationale.** Self-critique without external signal does not improve LLM reasoning (Huang 2023); tool-grounded critique does (Gou 2023). Atomic-claim decomposition makes verification more reliable (Min 2023). Persuasive prose sways judges independently of truth (Khan 2024; Zheng 2023); withholding it closes that channel. A single agent has no cross-run outcome library and does not falsify its own claims. Stage: critique and selection.

**Assumptions.** About 40% of claims are checkable by a 30 s numpy script or a lookup.; Falsified-claim rate in a top-3 tracks rater or outcome preference.

**How it fails.** Rigged checks (unconditional FAIL); mitigated by the consume-the-numbers rule and a 10% third-family audit.; Qualitative briefs yield mostly `not_checkable`; s ~ 0 discriminates nothing.; Generators hedge claims into unfalsifiable form; the 3-claim floor only partly blocks this.

**Cheapest test.** One brief, critique run twice at equal tokens: prose-only (off) vs ledger (on). A held-out model family re-runs extractor plus checker over both top-3s and the single agent's top 3; report falsified-claim rate and blinded panel ranking. No sandbox code was run.

**Effort.** One week; critique-phase tokens +30-50%.

**Operational spec.** Script: last stdout line PASS|FAIL, 30 s, numpy/scipy, no network. Lookup: cosine >= 0.85, k = 5. s = P - 2F; min-checkable 3; tie-break BT. Off-switch `critique.mode = prose|ledger`, equal tokens.


## Pair p02

## Idea X: Check-repair development loop with a cross-run library of check templates

**Pitch.** A bounded repair loop sees only failed checks and must pass or strike them; every executed check becomes a reusable cross-run template.

**Mechanism.** Repair loop, at most 3 iterations, on the critique-phase claim ledger. The developer sees only FAIL or INCONCLUSIVE ledger rows with check output, no critic prose. Per row: (1) revise the card; claims are re-extracted from the new text and the frozen check re-run must pass; (2) strike the claim; (3) contest with a counter-check; a third-model-family adjudicator picks the check faithful to the claim's wording, else INCONCLUSIVE. After iteration 3 every non-PASS claim is struck; a struck load-bearing claim flags the card, ranking it below unflagged cards. Each executed check enters the idea library as a parameterised template; check-authoring prompts get the top-3 templates at cosine > 0.8, to parameterise rather than rewrite. Final cards show no badges or check text.

**Rationale.** Code self-repair improves with execution feedback (Chen 2023) but the gain is bounded by feedback quality (Olausson 2023), motivating the 3-iteration cap and check outcomes over prose. Voyager's (Wang 2023) library of verified executable skills lets later episodes reuse rather than re-improvise. A single agent has no prior runs to borrow checks from.

**Assumptions.** A claim ledger with load-bearing flags exists at development time.; Claim patterns recur across briefs, so templates get reused.

**How it fails.** Developers weaken claims to triviality; the load-bearing flag penalises this; diagnostic: claims per final card.; Revisions overfit frozen checks; held-out checking detects it.; A wrong template propagates across runs; dropped once its adjudicator-contested rate exceeds 30%.

**Cheapest test.** 10 briefs, development at equal tokens: one-shot plus matched-token prose feedback (off) vs repair loop (on). Primary: blinded held-out-family panel ranks each arm's top 3 against the single agent's. Secondary: held-out falsified-claim rate; strikes per idea; template reuse. Kill if repair beats one-shot under 55%, or held-out falsified rate does not fall. No sandbox code was run.

**Effort.** One to two weeks; development tokens roughly 2x.

**Operational spec.** for it in 1..3: rows = ledger.where(outcome in {FAIL, INCONCLUSIVE}); developer(rows, templates) -> revise | strike | contest; re-extract, re-execute; contested -> adjudicator. Retrieval: cosine > 0.8, k = 3, exclude contested_rate > 0.3. Flags: `develop.mode = oneshot|repair`, `develop.max_iter = 3`, `templates.enabled`.


## Idea Y: Check-repair development loop with a cross-run library of check templates

**Pitch.** A bounded repair loop sees only failed checks and must pass or strike them; every executed check becomes a reusable cross-run template.

**Mechanism.** Repair loop, at most 3 iterations. The developer receives ledger rows with outcome FAIL or INCONCLUSIVE, plus check output, no critic prose. Options per row: (1) revise the idea until the same check passes on re-execution; (2) strike the claim; (3) contest with a counter-check, adjudicated by a third-model-family role that picks the check faithful to the claim's wording, else INCONCLUSIVE. After iteration 3 every non-PASS claim is struck. Each executed check is stored in the idea library as a parameterised template; prompts authoring a check are prepended with the top-3 templates at cosine > 0.8, to parameterise rather than rewrite. Final cards show no badges or check text.

**Rationale.** Code self-repair improves with execution feedback (Chen 2023) but the gain is bounded by feedback quality (Olausson 2023), motivating the 3-iteration cap and concrete check outcomes instead of prose. Voyager (Wang 2023) shows an accumulating library of verified executable skills lets later episodes reuse rather than re-improvise. A single agent has no prior runs to borrow checks from. Stage: development, compounding across runs.

**Assumptions.** Card 0's ledger or an equivalent set of executable checks exists at development time.; Claim patterns recur across briefs enough for templates to be reused.

**How it fails.** Developers weaken claims to triviality; diagnostic: claims per final card and rater specificity scores.; A wrong template propagates across runs; mitigated by dropping templates with adjudicator-contested rate above 30%.

**Cheapest test.** Same brief, development run twice at equal tokens: one-shot (off) vs repair loop (on). Outcomes: falsified-claim rate of the top 3 under a held-out checker of another model family; claims struck per idea; template reuse rate on a second brief. No sandbox code was run.

**Effort.** One to two weeks; development tokens roughly 2x.

**Operational spec.** for it in 1..3: rows = ledger.where(outcome in {FAIL, INCONCLUSIVE}); developer(rows, templates) -> revise | strike | contest; re-execute; contested -> adjudicator. Retrieval: cosine > 0.8, k = 3, exclude contested_rate > 0.3. Flags: `develop.mode = oneshot|repair`, `develop.max_iter = 3`, `templates.enabled` isolates library from loop.


## Pair p03

## Idea X: Claim ledger with executable checks; survival scored on checks passed

**Pitch.** Falsifiable claims replace prose critique; scripts, codebase probes and library lookups decide them, so ideas advance on checks passed, not eloquence.

**Mechanism.** New phase `claim_extraction` before critique: a different-family extractor rewrites each sketch into 4-8 typed claims with tolerances. Every critic objection carries exactly one artifact: (a) a sandbox script consuming the claim's numbers, printing PASS/FAIL; (b) a codebase probe (named hook, config key or metric exists); (c) a lookup of past ideas at cosine >= 0.85 (novelty FAILs on a falsified hit); or (d) `not_checkable`, weight 0. Errors or timeouts = INCONCLUSIVE. Score s = P - 2F ranks ideas into development; the selector sees only the ledger, never critic prose. Cards with under 3 checkable claims get the pool's median s, not last place; ties break by BT.

**Rationale.** Self-critique without external signal does not improve reasoning (Huang 2023); tool-grounded critique does (Gou 2023). Atomic claims make verification more reliable (Min 2023). Persuasive prose sways judges independently of truth (Khan 2024; Zheng 2023). Qualitative briefs like this one still make checkable feasibility claims ('implementable in this codebase'), which probes decide. A single agent has no cross-run outcome library.

**Assumptions.** Over 25% of claims per card are checkable (tested in step 0).; Falsified-claim rate in a top-3 tracks rater or outcome preference.

**How it fails.** Rigged checks; mitigated by the consume-the-numbers rule and a 10% third-family audit.; Purely aesthetic briefs yield few checkable claims; ranking reverts to BT: null, not harm.; Generators hedge claims into unfalsifiable form; other-family extraction partly blocks this.

**Cheapest test.** Step 0: one extractor call per saved benchmark card; measure checkable fraction by brief type; kill if median < 25%. Step 1: one brief, critique twice at equal tokens, prose (off) vs ledger (on); a held-out family re-checks both top-3s and the single agent's; report falsified-claim rate and blinded panel ranking. No code run.

**Effort.** One week; critique-phase tokens +30-50%.

**Operational spec.** Script: last stdout line PASS|FAIL, 30 s, numpy/scipy, no network. Probe: grep, import or dry-run. Lookup: cosine >= 0.85, k = 5. s = P - 2F; under 3 checkable: pool-median s; tie-break BT. Off-switch `critique.mode = prose|ledger`.


## Idea Y: Claim ledger with executable checks; survival scored on checks passed

**Pitch.** Falsifiable claims replace prose critique; sandbox runs and library lookups decide them, so ideas advance on checks passed, not eloquence.

**Mechanism.** New phase `claim_extraction` before critique: an extractor role (different model family) rewrites each sketch into 4-8 typed claims, each with a tolerance. Every critic objection must carry exactly one artifact: (a) a sandbox script that consumes the claim's numbers and prints PASS/FAIL; (b) a library lookup of past ideas at cosine >= 0.85 with recorded outcomes and falsifications (a novelty claim FAILs on a falsified hit); or (c) `not_checkable`, weight 0. The state machine runs artifacts; errors or timeouts = INCONCLUSIVE. Score s = P - 2F (P passed, F falsified) ranks ideas into development. The selector sees only the ledger, never critic prose. Cards with under 3 checkable claims rank last.

**Rationale.** Self-critique without external signal does not improve LLM reasoning (Huang 2023); tool-grounded critique does (Gou 2023). Atomic-claim decomposition makes verification more reliable (Min 2023). Persuasive prose sways judges independently of truth (Khan 2024; Zheng 2023); withholding it closes that channel. A single agent has no cross-run outcome library and does not falsify its own claims. Stage: critique and selection.

**Assumptions.** About 40% of claims are checkable by a 30 s numpy script or a lookup.; Falsified-claim rate in a top-3 tracks rater or outcome preference.

**How it fails.** Rigged checks (unconditional FAIL); mitigated by the consume-the-numbers rule and a 10% third-family audit.; Qualitative briefs yield mostly `not_checkable`; s ~ 0 discriminates nothing.; Generators hedge claims into unfalsifiable form; the 3-claim floor only partly blocks this.

**Cheapest test.** One brief, critique run twice at equal tokens: prose-only (off) vs ledger (on). A held-out model family re-runs extractor plus checker over both top-3s and the single agent's top 3; report falsified-claim rate and blinded panel ranking. No sandbox code was run.

**Effort.** One week; critique-phase tokens +30-50%.

**Operational spec.** Script: last stdout line PASS|FAIL, 30 s, numpy/scipy, no network. Lookup: cosine >= 0.85, k = 5. s = P - 2F; min-checkable 3; tie-break BT. Off-switch `critique.mode = prose|ledger`, equal tokens.


## Pair p04

## Idea X: Check-repair development loop with a cross-run library of check templates

**Pitch.** A standalone repair loop on finalists sees only failed checks and must pass or strike them; each executed check becomes a reusable cross-run template.

**Mechanism.** Finalists only. Uses I005's ledger if present, else a different-family extractor pulls up to 5 claims per finalist and writes their checks (sandbox script or codebase probe). At most 2 iterations, capped at 1.4x baseline development tokens. The developer sees only FAIL or INCONCLUSIVE rows with check output. Per row: (1) revise until the check passes on re-execution; (2) strike the claim; (3) contest with a counter-check; a third-family adjudicator picks the check faithful to the claim. After the last iteration non-PASS claims are struck; cards left under 3 claims revert to original. Each executed check becomes a parameterised library template; check-authoring prompts get the top-3 at cosine > 0.8. No badges: repairs reach raters as body text (corrected numbers, removed overclaims).

**Rationale.** Code self-repair improves with execution feedback (Chen 2023) but gains are bounded by feedback quality (Olausson 2023), motivating the cap and check outcomes over prose. Voyager (Wang 2023) shows a growing library of verified skills lets later episodes reuse, not re-improvise. A single agent has no prior runs' checks to reuse.

**Assumptions.** Finalists hold checkable claims (rate measured first).; Claim patterns recur across briefs, so templates get reused.

**How it fails.** Developers weaken claims to triviality; the 3-claim floor and other-family extraction limit this; diagnostic: rater specificity.; A wrong template propagates; templates contested over 30% are dropped.

**Cheapest test.** Offline on saved finalist cards, without I005: one-shot (off) vs repair (on) at equal development tokens. Outcomes: top-3 falsified-claim rate under a held-out other-family checker; blinded win rate vs the single agent's top 3; claims struck per idea; template reuse on a second brief. Kill if win rate does not rise or most claims are struck. No code run.

**Effort.** One to two weeks; development tokens capped at +40%.

**Operational spec.** ledger = I005 or extract(finalist, k<=5); for it in 1..2 while tokens < 1.4x: rows = ledger.where(outcome in {FAIL, INCONCLUSIVE}); developer(rows, templates) -> revise | strike | contest; re-execute; contested -> adjudicator; final claims < 3 -> revert. cosine > 0.8, k = 3, exclude contested_rate > 0.3. Flags: `develop.mode = oneshot|repair`, `templates.enabled`.


## Idea Y: Check-repair development loop with a cross-run library of check templates

**Pitch.** A bounded repair loop sees only failed checks and must pass or strike them; every executed check becomes a reusable cross-run template.

**Mechanism.** Repair loop, at most 3 iterations. The developer receives ledger rows with outcome FAIL or INCONCLUSIVE, plus check output, no critic prose. Options per row: (1) revise the idea until the same check passes on re-execution; (2) strike the claim; (3) contest with a counter-check, adjudicated by a third-model-family role that picks the check faithful to the claim's wording, else INCONCLUSIVE. After iteration 3 every non-PASS claim is struck. Each executed check is stored in the idea library as a parameterised template; prompts authoring a check are prepended with the top-3 templates at cosine > 0.8, to parameterise rather than rewrite. Final cards show no badges or check text.

**Rationale.** Code self-repair improves with execution feedback (Chen 2023) but the gain is bounded by feedback quality (Olausson 2023), motivating the 3-iteration cap and concrete check outcomes instead of prose. Voyager (Wang 2023) shows an accumulating library of verified executable skills lets later episodes reuse rather than re-improvise. A single agent has no prior runs to borrow checks from. Stage: development, compounding across runs.

**Assumptions.** Card 0's ledger or an equivalent set of executable checks exists at development time.; Claim patterns recur across briefs enough for templates to be reused.

**How it fails.** Developers weaken claims to triviality; diagnostic: claims per final card and rater specificity scores.; A wrong template propagates across runs; mitigated by dropping templates with adjudicator-contested rate above 30%.

**Cheapest test.** Same brief, development run twice at equal tokens: one-shot (off) vs repair loop (on). Outcomes: falsified-claim rate of the top 3 under a held-out checker of another model family; claims struck per idea; template reuse rate on a second brief. No sandbox code was run.

**Effort.** One to two weeks; development tokens roughly 2x.

**Operational spec.** for it in 1..3: rows = ledger.where(outcome in {FAIL, INCONCLUSIVE}); developer(rows, templates) -> revise | strike | contest; re-execute; contested -> adjudicator. Retrieval: cosine > 0.8, k = 3, exclude contested_rate > 0.3. Flags: `develop.mode = oneshot|repair`, `develop.max_iter = 3`, `templates.enabled` isolates library from loop.


## Output

Write one JSON object to `/home/user/agent-brainswarm/benchmark/experiments/loss-revision/out/gate-sonnet-1.json`: {"verdicts": [{"pair": "p01", "winner": "X or Y", "reason": "one sentence"}]}, one verdict per pair.
