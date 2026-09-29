# Single-agent baseline task (ETF strategy brief)

You are one strong agent asked to generate ideas for the brief below. Work alone. Do not use
web search or web fetch (the brainswarm run this is compared with had web research off).

## Brief

Design a rule-based, long-only trading strategy for a universe of 10 liquid ETFs (US large cap, US small cap, developed ex-US, emerging markets, US Treasuries 7-10y, TIPS, investment-grade credit, gold, broad commodities, US REITs). It must trade on at least 3 days per week, keep weekly turnover at or below 20%, and use only daily closing prices. Optimise long-run growth while keeping maximum drawdown below 20% and staying diversified across asset classes.

## Your job

1. Generate 20 distinct ideas: a title and a two-sentence pitch each.
2. Choose the 3 you would most want to pursue.
3. Develop each of those 3 into a full idea card of at most 400 words (title, pitch, mechanism,
   rationale, assumptions, failure modes, cheapest test, effort, operational spec). Be concrete:
   parameters, rules, and how each constraint in the brief is met.

## Output

Write one JSON object to the output path you were given:

```json
{"ideas": [{"title": "...", "pitch": "..."}],
 "top3": [{"title": "...", "pitch": "one sentence", "mechanism": "...", "rationale": "...",
           "assumptions": ["..."], "failure_modes": ["..."], "cheapest_test": "...",
           "effort": "...", "spec": "..."}]}
```

`ideas` has 20 entries; `top3` has 3 entries, best first.
