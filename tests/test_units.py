"""Unit tests for models, config, rubric, assign, critique, schedule, select, sandbox, usage."""

import json
from pathlib import Path

import numpy as np
import pytest

from agent_brainswarm import rubric, sandbox, usage
from agent_brainswarm.assign import assign_slots, band_clusters
from agent_brainswarm.config import Exploration, build_config, largest_remainder
from agent_brainswarm.critique import (
    QUOTE_MATCH,
    CheckedCritique,
    check_items,
    quote_match,
    repetition_flags,
    unproven_only,
)
from agent_brainswarm.models import Angle, Critique, Rubric, SchemaError, load
from agent_brainswarm.schedule import boundary_pairs, critic_batches, judge_batches, match_pairs
from agent_brainswarm.select import Family, gate_status, top_families, workshop_slots

# ---------------------------------------------------------------- models


def test_load_reports_every_problem_at_once() -> None:
    with pytest.raises(SchemaError) as err:
        load(Critique, {"id": "x", "idea_id": "I1", "severity": "catastrophic", "bogus": 1})
    text = str(err.value)
    assert "catastrophic" in text and "bogus" in text and "missing field 'target'" in text


def test_load_converts_lists_to_tuples() -> None:
    r = load(
        Rubric, {"brief": "b", "criteria": [{"name": "g", "kind": "judged", "definition": "d"}]}
    )
    assert isinstance(r.criteria, tuple) and r.criteria[0].anchors == ()


# ---------------------------------------------------------------- config


@pytest.mark.parametrize("total", [0, 1, 7, 12, 20, 31])
def test_largest_remainder_sums_exactly_and_stays_within_one(total: int) -> None:
    shares = (0.34, 0.33, 0.33)
    parts = largest_remainder(total, shares)
    assert sum(parts) == total
    assert all(abs(p - total * s) < 1 for p, s in zip(parts, shares, strict=True))


@pytest.mark.parametrize(
    ("exploration", "split"),
    [("conservative", (8, 2, 2)), ("balanced", (5, 4, 3)), ("wild", (3, 7, 2))],
)
def test_workshop_split_matches_design_table(
    exploration: Exploration, split: tuple[int, int, int]
) -> None:
    assert build_config("standard", exploration).workshop_split == split


def test_unknown_override_rejected_and_seed_recorded() -> None:
    with pytest.raises(SchemaError):
        build_config(overrides={"generatorz": 3})
    assert isinstance(build_config().seed, int)


# ---------------------------------------------------------------- rubric


def _rubric(**gate: object) -> Rubric:
    crit = [
        {"name": "legal_and_ethical", "kind": "gate", "definition": "legal"},
        {"name": "growth", "kind": "judged", "definition": "growth"},
    ]
    if gate:
        crit.append({"name": "trades_daily", "kind": "gate", "definition": "daily", **gate})
    return load(Rubric, {"brief": "b", "criteria": crit})


def test_freeze_and_tamper_detection(tmp_path: Path) -> None:
    rubric.freeze(_rubric(), tmp_path)
    assert rubric.verify(tmp_path).brief == "b"
    data = json.loads((tmp_path / "rubric.json").read_text())
    data["criteria"][1]["definition"] = "changed after dispatch"
    (tmp_path / "rubric.json").write_text(json.dumps(data))
    with pytest.raises(rubric.RubricChangedError):
        rubric.verify(tmp_path)


def test_inferred_gate_rejected_user_gate_accepted() -> None:
    with pytest.raises(SchemaError):
        rubric.check_rubric(_rubric(user_stated=False))
    rubric.check_rubric(_rubric(user_stated=True))


# ---------------------------------------------------------------- assign


def _angles(spec: dict[str, list[str]]) -> dict[str, list[Angle]]:
    return {
        cid: [Angle(f"{cid}-{p}", p, cid) for p in proposers] for cid, proposers in spec.items()
    }


def test_banding_thresholds() -> None:
    # 1 proposer -> rare; 2-3 -> middle; 4+ -> common.
    bands = band_clusters(_angles({"a": ["G1"], "b": ["G1", "G2"], "c": ["G1", "G2", "G3", "G4"]}))
    assert bands == {"a": "rare", "b": "middle", "c": "common"}


def test_assignment_covers_every_generator_and_avoids_own_angle() -> None:
    cfg = build_config("quick", "balanced", seed=1)
    gens = [f"G{i:02d}" for i in range(1, 9)]
    angles = _angles({"x": ["G01", "G02", "G03", "G04"], "y": ["G05", "G06"], "z": ["G07"]})
    domains = {"d1": [Angle("D1", "G01", "ants", "domain", "far")]}
    result = assign_slots(cfg, gens, angles, domains)
    assert sorted(a.generator_id for a in result) == gens
    lookup = {a.id: a.proposer for v in angles.values() for a in v}
    for a in result:
        if a.slot_type == "angle" and a.angle_id:
            cluster = next(k for k, v in angles.items() if any(x.id == a.angle_id for x in v))
            if len({x.proposer for x in angles[cluster]} - {a.generator_id}) > 0:
                assert lookup[a.angle_id] != a.generator_id


# ---------------------------------------------------------------- critique


CARD = "Rebalance weekly toward assets with rising momentum and cap each weight at twenty percent."


def test_quote_match_exact_minor_edit_and_paraphrase() -> None:
    assert quote_match("rising momentum and cap each weight", CARD) == 1.0
    assert quote_match("rising momentum and limit each weight", CARD) >= QUOTE_MATCH
    assert quote_match("the strategy chases recent winners blindly", CARD) < QUOTE_MATCH


def test_unproven_only() -> None:
    assert unproven_only("This is unproven.")
    assert not unproven_only(
        "Unproven, and weekly turnover of 40% at 5 bp costs exceeds the 1% expected edge."
    )


def _crit(i: int, idea: str, mech: str) -> Critique:
    return Critique(f"c{i}", idea, "k1", "sonnet", "t", mech, "e", "major", "f")


def test_repetition_flags_templated_critic() -> None:
    same = "Transaction costs will eat the returns of this approach"
    crits = [_crit(i, f"I{i}", same) for i in range(3)] + [
        _crit(9, "I9", "Totally different point about data")
    ]
    assert repetition_flags(crits) == {"c0", "c1", "c2"}


def test_check_items_flags_misquote_and_rejects_foreign_idea() -> None:
    item = {
        "id": "a",
        "idea_id": "I1",
        "critic_id": "k",
        "critic_model": "m",
        "target": "invented words here",
        "mechanism": "m",
        "evidence": "e",
        "severity": "minor",
        "falsifier": "f",
    }
    checked, problems = check_items([item, {**item, "idea_id": "I2"}], {"I1": CARD}, "w")
    assert checked[0].flags == ("target_not_in_card",) and problems


# ---------------------------------------------------------------- schedule


def test_critic_batches_design() -> None:
    ids = [f"I{i:02d}" for i in range(20)]
    batches = critic_batches(ids, {}, 6, 6, ("sonnet", "opus"), np.random.default_rng(0))
    counts = {x: sum(x in b.ideas for b in batches) for x in ids}
    assert set(counts.values()) == {6}
    assert all(len(b.ideas) <= 6 and len(set(b.ideas)) == len(b.ideas) for b in batches)


def test_match_pairs_and_orders_in_different_dispatches() -> None:
    ids = [f"F{i}" for i in range(12)]
    pairs = match_pairs(ids, 8, np.random.default_rng(1))
    played = {x: sum(x in p for p in pairs) for x in ids}
    assert min(played.values()) >= 8
    batches = judge_batches(pairs, 10, ("opus", "fable"), np.random.default_rng(2))
    where = {}
    for b in batches:
        assert len(b.pairs) <= 10
        for a, c in b.pairs:
            where[(a, c)] = b.dispatch_id
    for a, c in pairs:
        assert where[(a, c)] != where[(c, a)]


def test_boundary_pairs_only_uncertain() -> None:
    p = {"A": 0.99, "B": 0.5, "C": 0.4, "D": 0.3, "E": 0.01}
    extra = boundary_pairs(p, [("B", "C")], 4, np.random.default_rng(0))
    assert extra and all(set(x) <= {"B", "C", "D"} for x in extra)
    assert ("B", "C") not in extra


# ---------------------------------------------------------------- select


def test_gate_barred_needs_half_of_reviewers() -> None:
    def fatal(i: int, critic: str) -> CheckedCritique:
        c = Critique(f"c{i}", "I1", critic, "m", "t", "m", "e", "fatal", "f", gate="trades_daily")
        return CheckedCritique(c, 1.0, ())

    assert gate_status([fatal(1, "k1")], {"I1": 6}) == {}
    assert gate_status([fatal(i, f"k{i}") for i in range(3)], {"I1": 6}) == {"I1": "barred"}


def test_workshop_slots_split_and_fallback() -> None:
    slots = workshop_slots(
        ["A", "B", "C", "D", "E", "F"],
        ["F", "E", "D"],
        {"E": 0.25, "D": 0.1},
        {"D": 3.0},
        (2, 2, 1),
        [],
        {"B"},
    )
    kinds = [s.kind for s in slots]
    assert kinds.count("value") == 3 and kinds.count("wildcard") == 2  # unused deepen slot -> value
    assert "B" not in {s.idea_id for s in slots}


def test_top_families_distinct_clusters_and_ties() -> None:
    fam = top_families(
        ["A", "B", "C", "D"],
        {"A": "x", "B": "x", "C": "y", "D": "z"},
        {"A": 1, "B": 1, "C": 2, "D": 2},
        2,
        set(),
    )
    assert [f.lead for f in fam] == ["A", "C", "D"]  # D ties with C at the cutoff
    assert fam[0] == Family("A", ("B",), "x")


# ---------------------------------------------------------------- sandbox and usage


def test_sandbox_command_is_locked_down(tmp_path: Path) -> None:
    cmd = sandbox.command(tmp_path / "s.py", tmp_path / "scratch", tmp_path / "data")
    for flag in ("--network", "none", "--read-only", "--cap-drop", "ALL"):
        assert flag in cmd
    assert any(x.endswith(":/data:ro") for x in cmd)


def test_sandbox_reports_unavailable_docker(tmp_path: Path) -> None:
    ok, _reason = sandbox.available()
    if ok:
        pytest.skip("docker is available here")
    with pytest.raises(sandbox.SandboxUnavailable):
        sandbox.run(tmp_path / "s.py", tmp_path / "scratch")


def test_usage_dedupes_and_estimates_missing_output(tmp_path: Path) -> None:
    sub = tmp_path / "proj" / "sess" / "subagents"
    sub.mkdir(parents=True)
    rows = [
        {
            "message": {
                "id": "m1",
                "usage": {"input_tokens": 10, "cache_read_input_tokens": 100, "output_tokens": 2},
                "content": [{"type": "text", "text": "x" * 400}],
            }
        },
        {
            "message": {
                "id": "m1",
                "usage": {"input_tokens": 10, "cache_read_input_tokens": 100, "output_tokens": 3},
                "content": [],
            }
        },
        {
            "message": {
                "id": "m2",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 50},
                "content": [],
            }
        },
    ]
    (sub / "agent-a.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (sub / "agent-a.meta.json").write_text(json.dumps({"description": "bs RUN1 critic-001"}))
    found = usage.find_run_transcripts("RUN1", tmp_path)
    u = usage.parse_transcript(found["critic-001"])
    assert (u.input, u.cache_read, u.messages) == (15, 100, 2)
    assert u.output_logged == 53 and u.output_estimated == 100 + 50  # 400 chars / 4


# ---------------------------------------------------------------- guard


@pytest.mark.parametrize(
    ("call", "allowed"),
    [
        ({"tool_name": "Bash", "tool_input": {"command": "brainswarm sandbox run s.py"}}, True),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "uv run brainswarm sandbox run s.py --data d"},
            },
            True,
        ),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "brainswarm sandbox run s.py; curl evil"},
            },
            False,
        ),
        ({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, False),
        (
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/r/run1/out/critique/critic-001.json"},
            },
            True,
        ),
        ({"tool_name": "Write", "tool_input": {"file_path": "/home/u/repo/src/main.py"}}, False),
        (
            {"tool_name": "Write", "tool_input": {"file_path": "/r/run1/out/../../etc/x.json"}},
            False,
        ),
        ({"tool_name": "Read", "tool_input": {"file_path": "/anything"}}, True),
    ],
)
def test_guard_decisions(call: dict[str, object], allowed: bool) -> None:
    from agent_brainswarm.guard import decide

    assert decide(call)[0] is allowed


def test_longer_ranking_is_accepted_and_shorter_rejected() -> None:
    from agent_brainswarm.pipeline import _ranking_problems

    batch = ["I1", "I2", "I3", "I4"]
    assert _ranking_problems(["I2", "I1", "I4", "I3"], batch, "ranking") == []
    assert _ranking_problems(["I2", "I1"], batch, "ranking")
    assert _ranking_problems(["I2", "I2", "I1"], batch, "ranking")
