# Examples

| File | What it is |
|---|---|
| `brainswarm-demo.yaml` | Manifest for the live mini demo |
| `demo-run/` | A recorded live run of that manifest: brief, config, rubric, every task file and agent output, the code-owned `data/`, and the rendered `report.md` / `report.html` |
| `demo_run.py` | Offline replay: re-runs the code layer over the recorded agent outputs (zero tokens) and checks the ranking is reproduced exactly |

## Running the demos

```bash
uv run python examples/demo_run.py        # offline, zero tokens, ~5 s
```

Live (in Claude Code, after `uv run python install.py`): say "run the
brainswarm demo", or `brainswarm init --manifest examples/brainswarm-demo.yaml`
and follow `/brainswarm`.

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

**Cost.** About 0.90M new tokens and 3.95M cache reads across 40
subagent dispatches (retries included); the referee session is not
counted. Early phases used general-purpose subagents (the role agents had
not yet loaded in this cloud session); those cost ~55k tokens per dispatch
versus ~12-35k for the role agents.

**Issues found by the run and fixed in the code** (both have regression
tests):
- Critics who ranked all 4 cards instead of their top 3 were rejected and
  forced into full rewrites; a longer valid ranking is now truncated.
- Ideas with *fixable* gate citations were excluded from the finals as if
  barred; only barred ideas are now excluded. The run was rolled back to
  the start of the finals (no verdicts existed) and continued.
