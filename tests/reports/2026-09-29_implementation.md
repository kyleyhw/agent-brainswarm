# Implementation test report — 2026-09-29

## Summary

| Item | Value |
|---|---|
| Suite | `tests/` (4 files, 49 test functions; parametrisation expands them to 63 cases) |
| Result | 63 passed, 0 failed |
| Runtime | 9.26 s (pytest-reported); 9.7 s wall-clock including `uv run` start-up |
| Slowest | end-to-end library run 1.79 s; replay 1.48 s; export 0.89 s |
| Environment | Python 3.12.3 (uv-managed venv), pytest 9.1.1, numpy 2.5.3, choix (cross-check), Linux |
| Static checks | `ruff check`, `ruff format --check`, `ty check`: pass; pre-commit (ruff, ruff-format, secret scanning, ty): pass |
| Separate study | `docs/studies/uncertainty_coverage.py`: 176 s; results in `DESIGN.md` §10 |

## Scoring (`tests/test_scoring.py`)

| Test | What and why | Inputs and their rationale |
|---|---|---|
| two-idea closed form | The fit must reproduce the analytic MLE $\beta_A - \beta_B = \log(w_{AB}/w_{BA})$ | 4-2 record with balanced presentation orders (so $\gamma \to 0$) and prior scale 100 (penalty negligible); expected $\ln 2$ |
| sum to zero | Centring must follow from stationarity, not be imposed | three ideas, $\tau = 1.5$; checks $\sum \beta = 0$ to $10^{-9}$ |
| unique maximum | Strict concavity implies the same optimum from any start | default start vs an arbitrary start $(3, -2, 1, 0.7)$ |
| undefeated idea finite | The prior must keep an all-wins idea finite | 6-0 record |
| position bias recovered | $\gamma$ must be identifiable from ordered verdicts | 400 matches simulated from known $\beta = (1, 0.5, 0, -0.5, -1)$ and $\gamma = 0.8$; recovered within 0.3 and correct order |
| PL two-item = pair | Rankings and pairs must share one set of strengths | a 2-item ranking duplicated vs two balanced pair events |
| matches choix | Cross-check against an independent implementation | 6 ideas, all ordered pairs x 6, symmetric data; within 0.15 logits of `choix.ilsr_pairwise` |
| components | Disconnected graphs must be detected | A-B and C-D only |
| mean win | Bounds and symmetry of $\bar p$ | $\beta = (1, 0, -1)$: middle idea 0.5, extremes sum to 1 |
| Laplace below threshold | Method selection by cluster count | 5 events in < 30 clusters |
| bootstrap above threshold | Bootstrap path and ordering | 40 clusters of a clear A > B > C pattern |

## Units (`tests/test_units.py`)

- **Models**: every schema problem reported at once (bad literal, unknown
  field, missing field in one input); lists become tuples.
- **Config**: largest-remainder rounding sums exactly and stays within one
  unit of the target for totals 0, 1, 7, 12, 20, 31 (edge, small, and
  standard sizes); workshop splits equal the design table for all three
  exploration settings; unknown overrides rejected; seed recorded.
- **Rubric**: freeze, then tampering after freeze raises; inferred gates
  rejected, user-stated gates accepted.
- **Assign**: banding thresholds at popularities 1, 2, 4 (the three band
  edges); every generator assigned; nobody receives their own angle when an
  alternative exists.
- **Critique**: exact quote = 1.0; one-word edit >= 0.85; paraphrase < 0.85;
  "unproven" alone flagged, "unproven" plus a mechanism not; templated
  critic flagged on 3 ideas but not the distinct fourth; misquote flagged
  and foreign idea rejected.
- **Schedule**: every idea in exactly 6 batches of <= 6 with no duplicates
  (20 ideas, the standard ratio); every finalist in >= 8 matches and the two
  orders of every pair in different dispatches (12 finalists, standard);
  boundary pairs only among ideas with P(top-k) in [0.2, 0.8], never
  repeating a played pair.
- **Select**: gate barred only when half the reviewers raise a fatal gate
  critique (1 of 6 vs 3 of 6); unused deepen slots become value slots and
  barred ideas get none; families from distinct clusters with a tie at the
  cutoff included.
- **Guard**: 8 cases covering the allowed sandbox command, a command with
  `;` chaining, an arbitrary command, writes inside and outside `out/`,
  a `..` traversal, and an unrelated tool.
- **Sandbox**: the docker command contains `--network none`, `--read-only`,
  `--cap-drop ALL` and a read-only data mount; unavailable Docker raises
  (Docker's daemon is not reachable in this container, so the live path is
  untested here).
- **Usage**: message-id dedupe; output estimated as chars/4 when final
  usage is missing (400 characters -> 100 tokens); dispatch lookup via
  `bs <run> <id>` descriptions.
- **Ranking length**: a longer valid ranking accepted, a shorter or
  duplicated one rejected (regression from the demo).

## End to end (`tests/test_pipeline.py`)

Deterministic fake agents (`tests/fake_agents.py`) play every role; ideas
carry a hidden latent quality so recovery can be checked.

| Test | What it establishes |
|---|---|
| full run | Every phase runs; web-off skips fact-check; the finals leader has above-median hidden quality; the fake judges' built-in +0.4 position bias is detected with the right sign |
| retry then accept | An invalid JSON output is retried once with the problem logged, then accepted; nothing dropped |
| rubric tamper | Editing `rubric.json` after freeze stops the next phase |
| quick run | No workshop; finals among preliminary leaders |
| replay | Re-running the code over recorded outputs reproduces the final ranking exactly |
| library and champions | A second run imports 2 returning champions into its finals |
| export | Bundle with a parseable draft `agent-evolve.yaml` and hypotheses |
| CLI | `init` creates a run under `BRAINSWARM_HOME`; `validate` reads a manifest |
| fixable gates | Ideas with only fixable gate citations reach the finals (regression from the demo) |

## Packaging (`tests/test_packaging.py`)

Version format; every documented subcommand exists; skill frontmatter
parses as YAML and excludes "brainstorm"; every dispatched role has an
agent file whose frontmatter parses, names the role, and declares the guard
hook, and non-research roles have no web or shell; the installer links the
skill and all 9 agents into an isolated config directory, idempotently.

## Failures and fixes

- **Unquoted frontmatter** (packaging test): role descriptions contained
  `": "`, which made the YAML invalid, so Claude Code would not have loaded
  the agents. Fixed by quoting descriptions.
- **Run-id collision** (library test): two runs with the same seed in the
  same second got the same folder name. Fixed by retrying with a fresh
  suffix.
- **Always-true assertion** (ty): a version test that could not fail was
  replaced by a format check.
- **Weak retry test**: retries were not logged, so the test could not tell
  whether a retry happened. Retries are now logged and asserted.
- **Longer rankings rejected** (live demo): fixed by truncation; regression
  test added.
- **Fixable gates treated as barred** (live demo): all four developed ideas
  were excluded from the finals. Fixed; the regression test was confirmed
  to fail on the old code and pass on the new.
