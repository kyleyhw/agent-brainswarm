"""Digest, ``report.md``, and a self-contained ``report.html`` (DESIGN.md §9).

Principle: rank, don't remove; label, don't hide. Finalists are ranked by
the finals fit; every other idea is ranked below them by the critique fit.
The two strata are fitted on different objects (developed versus first
versions) and are never merged onto one scale.

The report is assembled as a list of blocks rendered twice, to Markdown
and to HTML, so the two never disagree.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from collections.abc import Sequence
from difflib import SequenceMatcher
from typing import Any

import numpy as np

from agent_brainswarm import library, records, usage
from agent_brainswarm.config import config_from_dict
from agent_brainswarm.critique import CheckedCritique
from agent_brainswarm.models import IdeaCard
from agent_brainswarm.scoring import Scores
from agent_brainswarm.select import top_families
from agent_brainswarm.state import Run

# Critiques of one idea at one severity whose mechanisms match above this
# ratio are shown once with a count; 0.6 merges shared phrasing of the same
# point while keeping distinct points apart (display only, never scoring).
MERGE_MATCH = 0.6

Block = tuple[Any, ...]


# --------------------------------------------------------------------------- scores I/O


def store_scores(run: Run, s: Scores, name: str) -> None:
    """Persist a scoring result to ``data/<name>``."""
    run.write(
        {
            "ids": list(s.fit.ids),
            "beta": [float(x) for x in s.fit.beta],
            "gamma": s.fit.gamma,
            "component": list(s.fit.component),
            "method": s.method,
            "draws": s.draws,
            "clusters": s.clusters,
            "rank": s.rank,
            "rank_interval": {k: list(v) for k, v in s.rank_interval.items()},
            "mean_win": s.mean_win,
            "p_top_k": s.p_top_k,
            "tier": s.tier,
            "unobserved_draw_fraction": s.unobserved_draw_fraction,
            "top_k_sensitivity": {k: list(v) for k, v in s.top_k_sensitivity.items()},
        },
        "data",
        name,
    )


def _scores(run: Run, name: str) -> dict[str, Any]:
    return dict(run.read("data", name)) if run.exists("data", name) else {}


# --------------------------------------------------------------------------- rendering


def _inline_html(text: str) -> str:
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", out)


def render_md(blocks: Sequence[Block]) -> str:
    """Blocks to Markdown."""
    out: list[str] = []
    for b in blocks:
        kind = b[0]
        if kind == "h":
            out.append("#" * b[1] + " " + b[2])
        elif kind == "p":
            out.append(b[1])
        elif kind == "list":
            out.append("\n".join(f"- {x}" for x in b[1]))
        elif kind == "table":
            headers, rows, caption = b[1], b[2], b[3]
            lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
            lines += [
                "| "
                + " | ".join(
                    str(c.get("md", c.get("text", ""))) if isinstance(c, dict) else str(c)
                    for c in r
                )
                + " |"
                for r in rows
            ]
            out.append(("\n".join(lines)) + (f"\n\n{caption}" if caption else ""))
        elif kind == "details":
            out.append(f"**{b[1]}**\n\n" + render_md(b[2]))
    return "\n\n".join(out) + "\n"


def render_html(blocks: Sequence[Block], title: str) -> str:
    """Blocks to a self-contained HTML page (inline CSS, no scripts)."""

    def body(bs: Sequence[Block]) -> str:
        parts: list[str] = []
        for b in bs:
            kind = b[0]
            if kind == "h":
                parts.append(f"<h{b[1]}>{_inline_html(b[2])}</h{b[1]}>")
            elif kind == "p":
                parts.append(f"<p>{_inline_html(b[1])}</p>")
            elif kind == "list":
                parts.append(
                    "<ul>" + "".join(f"<li>{_inline_html(x)}</li>" for x in b[1]) + "</ul>"
                )
            elif kind == "table":
                head = "".join(f"<th>{html.escape(h)}</th>" for h in b[1])
                rows = "".join(
                    "<tr>"
                    + "".join(
                        f"<td>{c['html']}</td>"
                        if isinstance(c, dict) and "html" in c
                        else f"<td>{_inline_html(str(c.get('text', '')) if isinstance(c, dict) else str(c))}</td>"
                        for c in r
                    )
                    + "</tr>"
                    for r in b[2]
                )
                cap = f"<caption>{_inline_html(b[3])}</caption>" if b[3] else ""
                parts.append(
                    f"<table>{cap}<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
                )
            elif kind == "details":
                parts.append(
                    f"<details><summary>{_inline_html(b[1])}</summary>{body(b[2])}</details>"
                )
        return "\n".join(parts)

    style = (
        ":root{--bg:#fff;--fg:#1d1d1f;--muted:#6e6e73;--line:#d2d2d7;--bar:#0a7cff;--band:#cfe3ff}"
        "@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#f2f2f4;--muted:#a1a1a6;"
        "--line:#3a3a3c;--bar:#4da3ff;--band:#1f3552}}"
        "body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;"
        "max-width:1100px;margin:0 auto;padding:16px}"
        "table{border-collapse:collapse;width:100%;margin:12px 0}"
        "th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}"
        "caption{caption-side:bottom;color:var(--muted);text-align:left;padding-top:6px}"
        "details{border:1px solid var(--line);border-radius:6px;padding:6px 10px;margin:8px 0}"
        "summary{cursor:pointer;font-weight:600}code{font-size:13px}"
        ".wrap{overflow-x:auto}"
    )
    return (
        f"<!doctype html><html lang=en><head><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{style}</style></head>"
        f"<body><div class=wrap>{body(blocks)}</div></body></html>\n"
    )


def _interval_svg(rank: int, lo: int, hi: int, n: int) -> str:
    """Rank interval as a horizontal bar on a 1..n axis (best at the left)."""
    width, pad = 160, 4
    scale = (width - 2 * pad) / max(n - 1, 1)

    def x(r: int) -> float:
        return pad + (r - 1) * scale

    return (
        f"<svg width={width} height=14 role=img aria-label='rank {rank}, interval {lo} to {hi} of {n}'>"
        f"<line x1={pad} y1=7 x2={width - pad} y2=7 stroke='var(--line)'/>"
        f"<rect x={x(lo):.1f} y=3 width={max(x(hi) - x(lo), 2):.1f} height=8 rx=3 fill='var(--band)'/>"
        f"<circle cx={x(rank):.1f} cy=7 r=3.5 fill='var(--bar)'/></svg>"
    )


# --------------------------------------------------------------------------- content


def _spearman(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) < 3:
        return None
    ra = np.argsort(np.argsort(np.asarray(a, dtype=np.float64)))
    rb = np.argsort(np.argsort(np.asarray(b, dtype=np.float64)))
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def _merged(items: Sequence[CheckedCritique]) -> list[tuple[CheckedCritique, int]]:
    groups: list[tuple[CheckedCritique, int]] = []
    for item in items:
        for i, (lead, n) in enumerate(groups):
            same = lead.critique.severity == item.critique.severity and lead.flags == item.flags
            if (
                same
                and SequenceMatcher(
                    None, lead.critique.mechanism.lower(), item.critique.mechanism.lower()
                ).ratio()
                >= MERGE_MATCH
            ):
                groups[i] = (lead, n + 1)
                break
        else:
            groups.append((item, 1))
    return groups


def _critique_blocks(
    chain: Sequence[str],
    crits: Sequence[CheckedCritique],
    responses: dict[str, Any],
) -> list[Block]:
    mine = [c for c in crits if c.critique.idea_id in chain]
    blocks: list[Block] = []
    for severity in ("fatal", "major", "minor"):
        items = [c for c in mine if c.critique.severity == severity]
        if not items:
            continue
        lines = []
        for lead, n in _merged(items):
            c = lead.critique
            resp = responses.get(c.id, {})
            status = resp.get("resolution", c.resolution)
            holds = resp.get("holds", [])
            if status == "rebutted" and holds:
                status += (
                    " (rebuttal held)"
                    if 2 * sum(holds) > len(holds)
                    else " (rebuttal did not hold)"
                )
            flags = f"; not counted: {', '.join(lead.flags)}" if lead.flags else ""
            count = f" (raised by {n} critics)" if n > 1 else ""
            gate = f" [gate: {c.gate}]" if c.gate else ""
            lines.append(
                f'**{status}**{gate}{count} on {c.idea_id}: "{c.target}" -> {c.mechanism} '
                f"*Evidence:* {c.evidence} *Falsifier:* {c.falsifier} "
                f"({c.critic_model}{flags})"
                + (f" *Response:* {resp['response']}" if resp.get("response") else "")
            )
        blocks.append(
            ("details", f"{severity.capitalize()} critiques ({len(items)})", [("list", lines)])
        )
    return blocks


def _card_blocks(card: IdeaCard) -> list[Block]:
    rows = [
        f"**Pitch.** {card.pitch}",
        f"**Mechanism.** {card.mechanism}",
        f"**Why it might work.** {card.rationale}",
        "**Assumptions.** " + "; ".join(card.assumptions),
        "**How it fails.** " + "; ".join(card.failure_modes),
        f"**Cheapest test.** {card.cheapest_test}",
        f"**Effort.** {card.effort}",
    ]
    if card.spec:
        rows.append(f"**Operational spec.** {card.spec}")
    if card.sources:
        rows.append("**Sources.** " + "; ".join(card.sources))
    p = card.provenance
    rows.append(
        f"*Provenance:* {p.generator_id} ({p.model}), slot {p.slot_type}"
        + (f", band {p.band}" if p.band else "")
        + (f", transfer {p.transfer}" if p.transfer else "")
        + (", research-derived" if p.research_derived else "")
    )
    return [("list", rows)]


def _chain(all_cards: dict[str, IdeaCard], idea: str) -> list[str]:
    ids = [idea]
    while all_cards[ids[-1]].parent_id:
        ids.append(all_cards[ids[-1]].parent_id or "")
    return ids


def build(run: Run) -> list[str]:
    """Write digest.txt, report.md, report.html, usage.json; update the library."""
    cfg = config_from_dict(run.read("config.json"))
    all_cards = records.cards(run)
    crits = records.all_critiques(run)
    responses = run.read("data", "responses.json") if run.exists("data", "responses.json") else {}
    prelim, final, novelty = (
        _scores(run, "prelim.json"),
        _scores(run, "final.json"),
        _scores(run, "novelty.json"),
    )
    gates: dict[str, str] = (
        run.read("data", "gates.json") if run.exists("data", "gates.json") else {}
    )
    cluster_of: dict[str, str] = run.read("data", "clusters.json")["cluster_of"]
    lib_rel: dict[str, Any] = run.read("data", "clusters.json")["library"]
    drift = set(run.read("data", "drift.json")) if run.exists("data", "drift.json") else set()
    slots = run.read("data", "slots.json") if run.exists("data", "slots.json") else []
    facts = run.read("data", "factcheck.json") if run.exists("data", "factcheck.json") else {}
    rubric_data = run.read("rubric.json")
    log = run.read("data", "log.json") if run.exists("data", "log.json") else []

    def root(x: str) -> str:
        return records.root_id(all_cards, x)

    def cluster(x: str) -> str:
        return cluster_of.get(root(x), root(x))

    barred = {x for x, v in gates.items() if v == "barred"}
    finalists: list[str] = sorted(final.get("ids", []), key=lambda x: final["rank"][x])
    n_final = len(finalists)
    families = top_families(
        finalists,
        {x: cluster(x) for x in finalists},
        final.get("tier", {}),
        cfg.top_k,
        {x for x in finalists if root(x) in barred},
    )
    lead_roots = {root(f.lead) for f in families}
    wild_pool = [
        records.latest(all_cards, s["idea_id"]).id
        for s in slots
        if s["kind"] in ("wildcard", "advocate") and s["idea_id"] not in lead_roots
    ]
    if not wild_pool and novelty:
        wild_pool = [
            x
            for x in sorted(novelty["ids"], key=lambda x: novelty["rank"][x])
            if x not in lead_roots
        ]
    wild_pool.sort(key=lambda x: -final.get("mean_win", {}).get(x, -1.0))
    wildcards = wild_pool[: cfg.wildcards_shown]

    # ---- limitations and bias metrics
    limitations: list[str] = []
    failed_lines = [x for e in log for x in e["lines"] if "failed" in x or x.startswith("dropped")]
    limitations += failed_lines
    if final.get("method") == "laplace":
        limitations.append(
            f"finals had only {final.get('clusters')} judge dispatches; uncertainty uses the Laplace approximation, not the bootstrap"
        )
    sens = final.get("top_k_sensitivity", {})
    if len({tuple(v) for v in sens.values()}) > 1:
        limitations.append("the top-k set changes with the prior scale; treat the cutoff as soft")
    if final.get("unobserved_draw_fraction", 0) > 0.05:
        limitations.append(
            "some bootstrap draws lacked data for an idea; its interval leans on the prior"
        )
    if len(set(final.get("component", [0]))) > 1:
        limitations.append(
            "the finals comparison graph is disconnected; ideas in different components are not comparable"
        )
    if drift:
        limitations.append(
            f"workshop drift (now effectively new ideas): {', '.join(sorted(drift))}"
        )
    limitations.append("scores measure judged preference by LLM judges, not whether an idea works")

    gamma = float(final.get("gamma", 0.0))
    length_rho = (
        _spearman(
            [len(all_cards[x].text().split()) for x in finalists],
            [final["rank"][x] for x in finalists],
        )
        if finalists
        else None
    )
    nov_rho = (
        _spearman(
            [novelty["rank"][x] for x in prelim.get("ids", [])],
            [prelim["rank"][x] for x in prelim.get("ids", [])],
        )
        if prelim and novelty
        else None
    )
    matches = run.read("data", "matches.json") if run.exists("data", "matches.json") else []
    same_model_wins = [
        (all_cards[m["first"]].provenance.model == m["judge_model"]) == (m["preferred"] == "first")
        for m in matches
        if (all_cards[m["first"]].provenance.model == m["judge_model"])
        != (all_cards[m["second"]].provenance.model == m["judge_model"])
    ]
    self_pref = sum(same_model_wins) / len(same_model_wins) if same_model_wins else None

    hits: dict[str, list[bool]] = defaultdict(list)
    for c in crits:
        resp = responses.get(c.critique.id)
        if not resp or not c.counts:
            continue
        if resp["resolution"] in ("fixed", "conceded"):
            hits[c.critique.critic_model].append(True)
        elif resp["holds"]:
            hits[c.critique.critic_model].append(2 * sum(resp["holds"]) <= len(resp["holds"]))

    # ---- usage
    transcripts = usage.find_run_transcripts(run.root.name)
    phase_of = {p.stem: p.parent.name for p in run.path("out").glob("*/*.json")}
    by_phase: dict[str, usage.Usage] = defaultdict(usage.Usage)
    for did, path in transcripts.items():
        by_phase[phase_of.get(did, "other")].add(usage.parse_transcript(path))
    total = usage.Usage()
    for u in by_phase.values():
        total.add(u)
    run.write(
        {
            "note": "subagents only; the referee session is not included; output is an estimate where final usage was not logged",
            "phases": {k: {**v.__dict__, "agents": len(v.agents)} for k, v in by_phase.items()},
        },
        "usage.json",
    )

    # ---- digest
    def fam_line(i: int, x: str) -> str:
        lo, hi = final["rank_interval"][x]
        return (
            f"{i}. {all_cards[x].title} [{x}]: rank {final['rank'][x]} (95% {lo}-{hi}), "
            f"P(top {cfg.top_k}) {final['p_top_k'][x]:.0%}, mean win {final['mean_win'][x]:.0%}"
        )

    digest = [
        f"brainswarm {run.root.name}: {len(all_cards)} cards, {len(finalists)} finalists ({cfg.size}/{cfg.exploration})"
    ]
    digest += ["Top families:"] + [fam_line(i + 1, f.lead) for i, f in enumerate(families)]
    if wildcards:
        digest += ["Wildcards:"] + [f"- {all_cards[x].title} [{x}]" for x in wildcards]
    if barred:
        digest.append(f"Barred by a gate (still in the report): {len(barred)}")
    if total.agents:
        digest.append(
            f"Tokens (subagents): ~{total.new_tokens / 1e6:.2f}M new, ~{total.cache_read / 1e6:.2f}M cache reads"
        )
    serious = [x for x in limitations[:-1]]
    if serious:
        digest.append("Limitations: " + "; ".join(serious[:3]))
    digest.append(f"Report: {run.path('report.html')}")
    run.path("digest.txt").write_text("\n".join(digest) + "\n")

    # ---- report blocks
    blocks: list[Block] = [
        ("h", 1, f"brainswarm report: {run.root.name}"),
        ("p", f"**Brief.** {run.brief.strip()}"),
        ("list", digest[1:-1]),
        ("h", 2, "Top idea families"),
        (
            "p",
            "Each family is the best-ranked finalist from a distinct cluster, with the other ideas from its cluster attached as variants. Ties at the cutoff are included.",
        ),
    ]
    for i, f in enumerate(families):
        card = all_cards[f.lead]
        variants = sorted(
            {
                y
                for y in all_cards
                if all_cards[y].version == 1 and cluster(y) == f.cluster and y != root(f.lead)
            }
        )
        blocks.append(("h", 3, f"{i + 1}. {card.title} ({f.lead})"))
        blocks += _card_blocks(card)
        if f.lead in facts:
            blocks.append(
                (
                    "list",
                    [
                        f"fact-check {c.get('status')}: {c.get('claim')} ({c.get('source', '')})"
                        for c in facts[f.lead]
                    ],
                )
            )
        if variants:
            blocks.append(
                ("p", "*Variants:* " + "; ".join(f"{all_cards[v].title} ({v})" for v in variants))
            )
        blocks += _critique_blocks(_chain(all_cards, f.lead), crits, responses)
    if wildcards:
        blocks.append(("h", 2, "Wildcards"))
        blocks.append(
            (
                "p",
                "Unusual ideas kept visible regardless of rank: most novel, most divisive among critics, or high upside with low probability.",
            )
        )
        for x in wildcards:
            blocks.append(("h", 3, f"{all_cards[x].title} ({x})"))
            blocks += _card_blocks(all_cards[x])
            blocks += _critique_blocks(_chain(all_cards, x), crits, responses)

    if finalists:
        rows = []
        for x in finalists:
            lo, hi = final["rank_interval"][x]
            rows.append(
                [
                    final["rank"][x],
                    {
                        "md": f"{lo}-{hi}",
                        "html": _interval_svg(final["rank"][x], lo, hi, n_final) + f" {lo}-{hi}",
                    },
                    final["tier"][x],
                    f"{final['p_top_k'][x]:.0%}",
                    f"{final['mean_win'][x]:.0%}",
                    f"{all_cards[x].title} ({x})" + (" [drift]" if x in drift else ""),
                ]
            )
        blocks += [
            ("h", 2, "Finalist ranking"),
            (
                "table",
                ["Rank", "95% rank interval", "Tier", f"P(top {cfg.top_k})", "Mean win", "Idea"],
                rows,
                (
                    f"Finalists ranked by the finals fit ({final.get('method')}, "
                    f"{final.get('clusters')} judge dispatches). The bar spans the 95% rank "
                    "interval on an axis from rank 1 (left) to last; the dot is the point "
                    "estimate. Overlapping bars mean the ideas cannot be reliably ordered; a new "
                    "tier starts only where the tier leader beats the next idea in at least 95% "
                    "of draws. Mean win is the average chance of beating each other finalist."
                ),
            ),
        ]

    if prelim:
        rows = []
        ids = sorted(prelim["ids"], key=lambda x: prelim["rank"][x])
        for x in ids:
            counts: dict[str, int] = defaultdict(int)
            for c in crits:
                if c.critique.idea_id == x and c.counts:
                    counts[c.critique.severity] += 1
            p = all_cards[x].provenance
            tags = [
                p.slot_type,
                p.band or "",
                p.transfer or "",
                "research-derived" if p.research_derived else "",
                lib_rel.get(x, {}).get("relation", ""),
            ]
            if x in gates:
                tags.append(f"gate:{gates[x]}")
            if any(s["idea_id"] == x for s in slots):
                tags.append("workshopped")
            lo, hi = prelim["rank_interval"][x]
            rows.append(
                [
                    prelim["rank"][x],
                    f"{lo}-{hi}",
                    novelty.get("rank", {}).get(x, ""),
                    f"{counts['fatal']}/{counts['major']}/{counts['minor']}",
                    ", ".join(t for t in tags if t),
                    f"{all_cards[x].title} ({x})",
                ]
            )
        blocks += [
            ("h", 2, "All ideas (critique stage)"),
            (
                "table",
                ["Rank", "95% interval", "Novelty rank", "Fatal/major/minor", "Tags", "Idea"],
                rows,
                (
                    "Every first-version idea, ranked by critics' batch rankings. This is a "
                    "separate scale from the finalist ranking and the two must not be compared. "
                    "Counts include only critiques that passed the code checks."
                ),
            ),
        ]
        blocks.append(("h", 2, "Every idea in full"))
        for x in ids:
            inner = _card_blocks(all_cards[x]) + _critique_blocks(
                _chain(all_cards, records.latest(all_cards, x).id), crits, responses
            )
            blocks.append(("details", f"{all_cards[x].title} ({x})", inner))

    internals: list[str] = [
        f"Position bias: gamma = {gamma:+.2f} logits, i.e. between equal ideas the first shown wins {1 / (1 + np.exp(-gamma)):.0%} of the time.",
        f"Length-rank correlation among finalists (Spearman): {length_rho:+.2f}"
        if length_rho is not None
        else "Length-rank correlation: n/a",
        f"Novelty-rank vs value-rank correlation (critique stage): {nov_rho:+.2f}"
        if nov_rho is not None
        else "Novelty correlation: n/a",
        f"Self-preference: judges picked the idea written by their own model in {self_pref:.0%} of mixed matches (50% = none)"
        if self_pref is not None
        else "Self-preference: n/a",
        "Top-k under prior scale: " + "; ".join(f"{k}: {', '.join(v)}" for k, v in sens.items()),
    ]
    internals += [f"Critic hit rate ({m}): {sum(v)}/{len(v)}" for m, v in sorted(hits.items())]
    blocks += [
        ("h", 2, "Limitations"),
        ("list", limitations),
        ("h", 2, "Run internals"),
        ("list", internals),
        (
            "details",
            "Frozen rubric",
            [
                (
                    "list",
                    [
                        f"**{c['name']}** ({c['kind']}): {c['definition']}"
                        for c in rubric_data["criteria"]
                    ]
                    + [f"Assumption: {a}" for a in rubric_data.get("assumptions", [])],
                )
            ],
        ),
        (
            "details",
            "Phase log",
            [("list", [f"[{e['phase']}] {x}" for e in log for x in e["lines"]])],
        ),
    ]
    if total.agents:
        rows = [
            [
                k,
                len(v.agents),
                f"{v.new_tokens:,}",
                f"{v.cache_read:,}",
                v.messages_without_final_usage,
            ]
            for k, v in sorted(by_phase.items())
        ]
        blocks.append(
            (
                "table",
                ["Phase", "Agents", "New tokens", "Cache reads", "Msgs w/o final usage"],
                rows,
                "Subagent usage parsed from transcripts; output tokens are estimated where the final usage entry was not logged. The referee session is not included.",
            )
        )

    run.path("report.md").write_text(render_md(blocks))
    run.path("report.html").write_text(render_html(blocks, f"brainswarm {run.root.name}"))

    # ---- library
    entries = []
    for x in sorted(k for k, c in all_cards.items() if c.version == 1 and not k.startswith("L")):
        latest = records.latest(all_cards, x)
        entries.append(
            {
                "card": run.read("data", "cards.json")[latest.id],
                "cluster": cluster(x),
                "finalist": latest.id in finalists,
                "mean_win": final.get("mean_win", {}).get(latest.id),
                "prelim_rank": prelim.get("rank", {}).get(x),
                "open_critiques": sum(
                    1
                    for c in crits
                    if c.critique.idea_id in _chain(all_cards, latest.id)
                    and c.counts
                    and responses.get(c.critique.id, {}).get("resolution", "open") == "open"
                ),
            }
        )
    refuted = [
        {"claim": c.get("claim", ""), "source": c.get("source", "")}
        for v in facts.values()
        for c in v
        if c.get("status") == "refuted"
    ]
    size = library.update(run, entries, refuted)
    return digest + [f"library now holds {size} ideas for project {run.status.get('project')}"]
