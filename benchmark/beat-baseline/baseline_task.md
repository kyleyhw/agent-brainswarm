# Single-agent baseline task (beat-baseline brief)

You are one strong agent asked to generate ideas for the brief below. Work alone. Do not use
web search or web fetch, and read no file other than this one (the brainswarm run this is compared with had web
research off and its generators saw only this text).

## Brief

Ways to make a multi-agent idea-generation system (independent generators, justified critique, development of selected ideas, LLM-judged pairwise finals) produce top ideas that measured outcomes or independent raters prefer over a single strong agent's self-selected top 3 for the same brief. Hard rules: each change must be implementable in this codebase and testable with the existing benchmark.

## Context (as given to the multi-agent run)

- **The system ("this codebase").** The change can be built within the existing system (a Python state machine that plans and checks each phase, role-agent prompts, a Bradley-Terry / Plackett-Luce scoring module, a sandbox for scratch code, and an idea library across runs), including by adding or changing phases, roles, prompts, schedules, scoring or the models assigned to roles. It fails only if it requires replacing the system.
- **The benchmark.** Its effect can be tested with the existing benchmark: for a brief, the system's top 3 ideas and a single strong agent's self-selected top 3 (from 20 ideas) are rendered in one card format, blinded, and rated and ranked by independent raters (a counterbalanced panel of LLM reviewers, or humans) or compared on measured outcomes where the brief allows them. It fails only if no such comparison could show its effect.

## Your job

1. Generate 20 distinct ideas: a title and a two-sentence pitch each.
2. Choose the 3 you would most want to pursue.
3. Develop each of those 3 into a full idea card of at most 400 words (title, pitch, mechanism,
   rationale, assumptions, failure modes, cheapest test, effort, operational spec). Be concrete.
   Each card must be self-contained: never refer to another idea or card ("as in Idea 1");
   repeat what is needed instead, because each card will be read on its own.

## Output

Write one JSON object to the output path you were given:

```json
{"ideas": [{"title": "...", "pitch": "..."}],
 "top3": [{"title": "...", "pitch": "one sentence", "mechanism": "...", "rationale": "...",
           "assumptions": ["..."], "failure_modes": ["..."], "cheapest_test": "...",
           "effort": "...", "spec": "..."}]}
```

`ideas` has 20 entries; `top3` has 3 entries, best first.
