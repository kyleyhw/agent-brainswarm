# Live verification and fixes — 2026-09-29

This report covers the follow-up to the first live demo: fixes for the problems it exposed, live
checks of the platform assumptions (guard hook, trigger, sandbox), and the regression tests
added for every defect found.

## Summary

| Item | Value |
|---|---|
| Suite | `tests/` (4 files; 69 cases after parametrisation) |
| Result | 69 passed, 0 failed, 0 skipped |
| Runtime | 21.40 s (pytest-reported); 21.8 s wall-clock including `uv run` start-up |
| Slowest | live sandbox isolation 6.67 s (Docker); replay branching 2.15 s; judge verdict checks 1.70 s |
| Environment | Python 3.12.3 (uv), pytest 9.1.1, numpy 2.5.3, Docker 29.3.1 with `quay.io/jupyter/scipy-notebook:latest`, Linux |
| Static checks | `ruff check`, `ruff format`, `ty check`, secret scanning (pre-commit): pass |
| Offline demo | `examples/demo_run.py` reproduces the recorded ranking exactly |

## Live checks

These ran against the real platform, not fakes. Where a check needed tokens its cost is given.

| Check | Why | Result |
|---|---|---|
| Guard hook fires for a role agent | The allowlist and hook were verified only through the hook's stdin interface | A generator probe made 5 calls: `ls /` blocked, `brainswarm sandbox run …` allowed, `sandbox run x.py; ls /` blocked, a write outside `out/` blocked, a JSON write under `out/` allowed (13k tokens) |
| Guard with the CLI off PATH | Claude Code blocks only on exit 2 | With the old hook command the write was **allowed**: the transcript records `hook_non_blocking_error`, exit 127, `brainswarm: not found`. Fixed (below) |
| Guard in a fresh cloud session, project-level agent | Sessions opened on this repository load the role agents from `.claude/agents/` | CLI absent, yet the probe's write **succeeded** and the transcript holds no hook record: the hook did not run. The documentation says project-level agent hooks need workspace trust, which cloud sessions do not grant. Mitigated by a referee self-test; relocation of the role files is an open decision |
| Trigger, "brainstorm …" | The skill must not fire on casual requests | Fresh cloud sessions answered directly (1 model call, no skill load) in all three runs |
| Trigger, "brainswarm …" | The skill must fire on its name | With the original description it did **not** fire (answered directly; 2 sessions). After the description was rewritten to lead with the trigger, it fired in both runs. Evidence is indirect: the sessions made a second model call and wrote ~3.1k extra tokens to cache, the size of `SKILL.md` (~2.1k tokens) plus the tool call |
| Skill and agents load in fresh sessions | Needed to interpret the trigger tests | A diagnostic session listed `brainswarm` among its skills and all nine role agents |
| Sandbox isolation | The live Docker path had never run | Network and DNS blocked; writes to `/etc` blocked; no host secrets visible; numpy importable. Found broken: scratch not writable, output lost on a memory kill, container left running after a timeout. Fixed (below) |

## Regression tests added

| Test | Defect it pins down | Inputs and their rationale |
|---|---|---|
| `test_judge_verdicts_name_winner_and_criterion` | Verdicts used first/second labels | A valid verdict naming the second-listed idea; then `winner: "first"`, a gate criterion (`trades_daily`, not a judged one), and strengths for only one idea, each of which must be rejected; legacy first/second verdicts still accepted so recorded runs replay |
| `test_match_pairs_and_orders_in_different_dispatches` (extended) | Position bias aliased with model disagreement | 12 finalists, 8 matches each, 2 models: both orders of every pair go to the same model in different dispatches, both models are used, and the verdict count equals the old design's |
| `test_replay_until_branches_a_live_run` | Branching a recorded run; branches sharing a library project | Fake run branched at the finals and finished by new agents; a second branch, renamed as side-by-side branches are, must have the same finalists (it imported the first branch's as champions). Confirmed to fail on the old code |
| `test_second_run_uses_library_and_champions[True]` | Fact-check read cards before champions were imported (KeyError) | Second run in a project with web on; confirmed to fail on the old order |
| `test_guard_hook_fails_closed[True/False]` | Missing CLI silently allowed every call | The hook command run by `sh -c` with a fake `brainswarm` on PATH (passes through, exit 0) and without it (exit 2, "not on PATH") |
| `test_usage_dedupes_and_estimates_missing_output` (extended) | Retries and repeated ids overwrote transcripts | Two transcripts under one description: both are kept |
| `test_sandbox_live_isolation` | Scratch not writable; output lost on a kill; leaked container | A probe that tries the network, `/etc`, `/work` and numpy, then allocates 2 GB (over the 1 GB limit): the four results must print and the exit code be 137. A 600 s sleep with the limit patched to 5 s: `timed_out`, partial output kept, no container left running. Confirmed to fail on the old code |
| `test_sandbox_reports_unavailable_docker` (rewritten) | Skipped on hosts where Docker runs | `shutil.which` patched to find no docker |

## Failures and fixes

- **Position bias** (live): a judge-prompt change reduced first-listed wins only from 11/12 to
  10/12; a crossover showed the bias is real (20/24, each model flipping in 4 of 6 pairs). Fixed
  by the crossover schedule; see `docs/studies/position_bias.md`.
- **Workshop word cap** (live): three of four cards over the cap in the demo; with a per-field
  budget, zero of four in the rerun.
- **Usage undercount**: repeated dispatch ids and retries overwrote transcripts; the demo's
  cost was at least 1.41M new tokens, not 0.90M. Fixed with phase-qualified descriptions.
- **Guard fail-open** (live): see the table above; the hook command now exits 2 when the CLI is
  missing and the guard turns any exception into exit 2.
- **Fact-check crash with champions**: found by the token-calibration study's fixture runs.
- **Replay library collision** (live): the second rerun branch imported the first branch's
  finalists; the run was rebuilt cleanly after the fix.
- **Trigger**: the original description did not fire on "brainswarm …"; rewritten.
- **Sandbox**: three defects above, all fixed and covered by the live test.
- **`γ > 0` assertion**: the end-to-end test asserted the fake judges' small bias is detected.
  Under the crossover schedule no pair flipped, so the estimate is exactly 0 by symmetry; the
  test now requires $\gamma$ not to be negative, and recovery is tested in `test_scoring.py`
  with 400 simulated matches.
