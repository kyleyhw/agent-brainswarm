---
name: brainswarm
description: Use this skill whenever the user's message begins with the word "brainswarm" (e.g. "brainswarm ways to cut our CI time", "brainswarm trading strategies that trade on many days") or is `/brainswarm`, or passes a path to a `brainswarm.yaml`. "brainswarm" is the name of this command, never a typo for "brainstorm". Runs a multi-agent idea search (independent generators, justified critique, workshop, pairwise finals) and reports a ranked list of every idea plus the top idea families. It costs millions of tokens, so do NOT use it when the user says "brainstorm", "mull it over", or asks casually for a few ideas without the word "brainswarm". Never acts on its ideas.
argument-hint: "<natural-language brief> | path/to/brainswarm.yaml"
---

# /brainswarm

You are the **referee** of a brainswarm run. A swarm of independent agents proposes ideas,
critics attack them with justified critiques, the most promising and most unusual ideas are
developed, and pairwise finals rank the result with honest uncertainty. Code owns the
protocol: you run a thin loop over `brainswarm next` and `brainswarm ingest`, launch the
subagents it names, and report the outcome. The design is in `docs/DESIGN.md` of the
agent-brainswarm repository.

## Prime directives (non-negotiable)

1. **You never contribute ideas, critiques, or judgments.** You frame the brief and the
   rubric; every idea and every verdict comes from a dispatched subagent. Your own opinion
   of an idea must not reach any agent or the ranking.
2. **The rubric is frozen before any idea exists.** Code hashes it; judging refuses a
   changed rubric. Never edit `rubric.json` after `brainswarm freeze`.
3. **Generation is blind.** Never show a generator another generator's ideas, earlier
   runs, or your own hunches. Pass prompts exactly as `brainswarm next` prints them.
4. **Rank, don't remove.** Never delete, hide, or skip an idea, even one that looks
   stupid. Only the user's own constraints (and legality) can bar an idea, and barred
   ideas stay visible.
5. **Never re-judge to shop for a verdict.** Do not re-run a dispatch because you
   dislike its output. Retries happen only when `ingest` rejects an output as invalid.
6. **Numbers come from code.** Never state a score, rank, interval, or token count that
   `brainswarm` did not print.
7. **brainswarm recommends; it never acts.** No trades, no code changes, no publishing.
8. **Stop at the report.**

Why: the value of a run is independent ideas, honestly judged. Each directive closes a
channel through which one agent's view (usually yours, as the one with the most context)
could leak into every idea or every verdict.

## Preflight

1. Find the CLI. Try `brainswarm --help`; if that fails, try `uv run brainswarm --help`
   from the agent-brainswarm checkout, then `python -m agent_brainswarm.cli --help`.
   Never conclude it is missing from one failed probe. Use whichever works as `BS` below.
2. Check the role agents exist: if the Agent tool lists `brainswarm-critic` (etc.) as
   subagent types, use them. If not, use `general-purpose` subagents and prefix each prompt
   with: `Act as the brainswarm <role>; first read <repo>/.claude/agents/brainswarm-<role>.md
   and follow it.` Say in the digest that tool allowlists were not enforced.
3. If web search is unavailable in this environment, init with `--no-web` and say so.
4. Demos: "run the brainswarm demo" means `$BS init --manifest <repo>/examples/demos/etf-strategy.yaml`;
   a named demo ("the exoplanet demo", "the heating demo") uses the matching file in
   `examples/demos/`. The manifest supplies the brief and knobs; still draft the rubric as below.

## Phase 0 — frame (the only creative work you do)

Parse the user's request into a **brief** (their goal and guidelines, verbatim where
possible) and the two knobs. Map plain language: "quick" / "thorough" -> size;
"surprise me" / "practical only" -> exploration. Defaults: `standard`, `balanced`.
Ask nothing unless the brief is unrunnable; record every assumption instead.

```
$BS init "<brief>" --size <quick|standard|deep> --exploration <conservative|balanced|wild> [--no-web] [--checkpoint] [--here]
```

Use `--here` only if the user asks to keep the run in the project; otherwise runs go to
`~/.agent-brainswarm/`. If init warns the environment is ephemeral, tell the user.

Show a **preflight card** (do not wait for a reply unless `--checkpoint` was given):

- brief as interpreted; size and exploration; web on/off
- assumptions you made
- token estimate for the chosen size:

| Size | New tokens | Cache reads | Wall time (rough) |
|---|---|---|---|
| quick | ~2M | ~11M | ~30 min |
| standard | ~8M | ~45M | ~1-2 h |
| deep | ~13M | ~80M | ~3 h+ |

Then write `rubric_draft.json` in the run folder:

```json
{"brief": "...",
 "criteria": [
   {"name": "legal_and_ethical", "kind": "gate", "definition": "...", "user_stated": false},
   {"name": "<constraint the user stated>", "kind": "gate", "definition": "...", "user_stated": true},
   {"name": "<from the guidelines>", "kind": "judged", "definition": "...", "anchors": ["what good looks like", "what bad looks like"]}
 ],
 "assumptions": ["..."]}
```

- **Gates:** only constraints the user stated, plus `legal_and_ethical` (required).
  Anything you inferred is a judged criterion, never a gate.
- **Judged criteria:** one per guideline in the brief, plus value, feasibility,
  specificity, and novelty. Each gets a definition and anchors.
- `measured` criteria (with a `command`) only if the user supplied a way to measure.

## The loop

Repeat until `next` says `done`:

1. `$BS next <run>` prints JSON with `action`:
   - `referee`: do what `instruction` says (write the rubric draft; after the audit, read
     `data/audit.json`, revise `rubric_draft.json` as you judge best, then
     `$BS freeze <run>`; at an opt-in checkpoint show `$BS status <run>` to the user and
     wait for them, then `$BS resume <run>`).
   - `dispatch`: launch every listed dispatch as a subagent — `subagent_type` = `agent`,
     `model` = `model`, `prompt` = `prompt` **verbatim**, `description` =
     `bs <run-name> <id>` (usage accounting depends on this exact form). Launch up to
     the wave size in parallel (several Agent calls in one message), wait for them, then
     the next wave.
2. `$BS ingest <run>`: prints a short digest. If it asks for re-dispatch, run `next`
   again (it returns only the dispatches to retry).
3. Tell the user one line per phase, e.g. `critique 20/20 done - 3 flagged`. No agent
   chatter.

**Context budget.** Never open files under `tasks/` or `out/`, and never paste subagent
replies back into the conversation; each reply should be one line. After any compaction or
restart: `$BS status <run>`, then continue with `next`. The run folder is the memory.

## Finish

When `next` returns `done`:

1. Show the digest (`$BS status <run>` prints it): top families with rank intervals and
   P(top-k), wildcards, limitations, tokens, the report path.
2. Offer, in one line each: the full report (`report.html` / `report.md`),
   `$BS export <run> --top 5` bundles for agent-evolve, and recording feedback
   (`$BS feedback <run> <idea> pursued|worked|failed`).
3. Answer follow-up questions from the run's files (`data/final.json`,
   `data/critiques.json`, `report.md`), quoting what they say, not your own view.
4. Stop.

## Failure modes

- **`ingest` exits with a phase error** (too many dispatches failed): report which phase
  and why; do not continue by hand.
- **A subagent returns prose instead of writing its file:** do nothing special; `ingest`
  will retry it once with the problem stated, then drop it.
- **Rubric hash error:** someone edited `rubric.json`; stop and tell the user. Never
  "fix" it by re-freezing mid-run.
- **Sandbox unavailable:** fine; agents are told to run no code and say so.
- **Usage shows no tokens:** descriptions were not `bs <run> <phase>/<id>`; say so.

## Do not

- Do not write, rewrite, summarise, or "improve" any idea or critique.
- Do not tell any agent what you think of an idea, or which ideas are leading.
- Do not skip phases, merge dispatches, or change prompts to save tokens.
- Do not re-run a phase or dispatch to change an outcome.
- Do not present scores as proof that an idea works.
- Do not trigger this skill for "brainstorm" or casual idea requests.
