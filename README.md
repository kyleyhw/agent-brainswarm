# agent-brainswarm

> **Status: design phase.** The protocol is specified in
> [`docs/DESIGN.md`](docs/DESIGN.md); the repo currently holds a scaffold
> only. `/brainswarm` will tell you it is not implemented yet.

**brainswarm generates ideas at scale and ranks them honestly.** Give it a
brief with guidelines and a swarm of independent agents researches and
proposes ideas, other agents critique every idea with justified criticism,
the most promising and most unusual ideas are developed further, and the
results are ranked with honest uncertainty. You get a ranked list of every
idea with its full critique record and the top few idea families, ready to
hand to [agent-evolve](https://github.com/kyleyhw/agent-evolve) if you want.

**brainswarm the ideas, evolve the code.**

```
brainswarm trading strategies that trade on many days and optimise growth and diversification
brainswarm ways to cut our CI time — quick, surprise me
/brainswarm path/to/brainswarm.yaml
```

Two knobs: **size** (`quick` / `standard` / `deep`, each with a token
estimate) and **exploration** (`conservative` / `balanced` / `wild`).

Like agent-evolve, this is a skills bundle you install once and use across
projects; read it as instructions you give to Claude.
