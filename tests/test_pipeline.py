"""End-to-end pipeline runs with fake agents (fixture mode): zero tokens."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from agent_brainswarm import cli, pipeline, rubric
from agent_brainswarm.config import build_config, config_to_dict
from agent_brainswarm.state import Run
from tests.fake_agents import quality, rubric_draft, write_outputs

BRIEF = "Come up with a stock trading strategy that trades on many days and optimises growth and diversification."


def small_config(**over: Any) -> dict[str, Any]:
    base = {
        "generators": 6,
        "ideas_per_generator": 2,
        "workshop_slots": 4,
        "finals_matches_per_idea": 3,
        "draws": 60,
        "web": False,
    }
    return config_to_dict(build_config("standard", "balanced", {**base, **over}, seed=11))


def new_run(tmp_path: Path, **over: Any) -> Run:
    return cli.create_run(BRIEF, small_config(**over), tmp_path / "runs", "test-project")


def drive(run: Run, max_steps: int = 60, sabotage: str | None = None) -> list[str]:
    """Play the referee: follow next_step until done. Returns the phases seen."""
    seen = []
    sabotaged = False
    for _ in range(max_steps):
        step = pipeline.next_step(run)
        seen.append(step["phase"])
        if step["action"] == "done":
            return seen
        if step["action"] == "referee":
            if step["phase"] == "rubric":
                run.write(rubric_draft(BRIEF), "rubric_draft.json")
            elif step["phase"] == "freeze":
                pipeline.freeze(run)
            elif step["phase"] == "checkpoint":
                pipeline.resume(run)
            continue
        write_outputs(run, step)
        if sabotage == step["phase"] and not sabotaged:
            first = step["dispatches"][0]["id"]
            run.path("out", step["phase"], f"{first}.json").write_text("{not json")
            sabotaged = True
        pipeline.ingest(run)
    raise AssertionError(f"did not finish; phases {seen}")


def test_full_run_reaches_report(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    phases = drive(run)
    for phase in (
        "audit",
        "angles",
        "angle_clusters",
        "ideate",
        "research",
        "idea_clusters",
        "critique",
        "checker",
        "advocate",
        "workshop",
        "recritique",
        "finals",
        "done",
    ):
        assert phase in phases
    assert "factcheck" not in phases  # web is off
    for name in ("report.md", "report.html", "digest.txt"):
        assert run.path(name).read_text().strip()
    final = run.read("data", "final.json")
    assert set(final["ids"]) and all(x.endswith("-v2") for x in final["ids"])
    # The finals recover the hidden quality order better than chance.
    cards = run.read("data", "cards.json")
    ranked = sorted(final["ids"], key=lambda x: final["rank"][x])
    q = [quality(cards[x]["title"]) for x in ranked]
    assert q[0] >= sorted(q)[len(q) // 2]
    # The fake judges' +0.4-logit position bias is too small to flip these 12 verdicts, so
    # gamma is ~0 here; it must not come out negative. Recovery is tested in test_scoring.
    assert final["gamma"] > -1e-9


def test_invalid_output_is_retried_then_accepted(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    drive(run, sabotage="critique")
    critique_log = json.dumps([e for e in run.read("data", "log.json") if e["phase"] == "critique"])
    assert "retry critic-" in critique_log and "not valid JSON" in critique_log
    assert "dropped" not in critique_log
    assert run.status["phase"] == "done"


def test_rubric_tamper_stops_the_run(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    run.write(rubric_draft(BRIEF), "rubric_draft.json")
    step = pipeline.next_step(run)  # audit dispatch
    write_outputs(run, step)
    pipeline.ingest(run)
    pipeline.freeze(run)
    data = run.read("rubric.json")
    data["criteria"][2]["definition"] = "tampered after dispatch"
    run.write(data, "rubric.json")
    with pytest.raises(rubric.RubricChangedError):
        pipeline.next_step(run)  # planning the angle round verifies the hash


def test_quick_run_has_no_workshop(tmp_path: Path) -> None:
    run = cli.create_run(
        BRIEF,
        config_to_dict(
            build_config("quick", "wild", {"generators": 5, "draws": 40, "web": False}, seed=3)
        ),
        tmp_path / "runs",
        "p",
    )
    phases = drive(run)
    assert "workshop" not in phases and "finals" in phases


def test_replay_reproduces_ranking_with_zero_agents(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    drive(run)
    replayed = cli.replay(run.root, tmp_path / "replay")
    assert replayed.read("data", "final.json")["rank"] == run.read("data", "final.json")["rank"]


@pytest.mark.parametrize("web", [False, True])
def test_second_run_uses_library_and_champions(tmp_path: Path, web: bool) -> None:
    # web=True regression: fact-check read cards before champions were imported (KeyError).
    first = new_run(tmp_path, web=web)
    drive(first)
    second = new_run(tmp_path, returning_champions=2, web=web)
    drive(second)
    champions = second.read("data", "champions.json")
    assert len(champions) == 2 and set(champions) <= set(second.read("data", "final.json")["ids"])


def test_export_bundle(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    drive(run)
    from agent_brainswarm import export

    lead = export.top_families(run)[0]
    folder = export.bundle(run, lead, tmp_path / "export")
    manifest = yaml.safe_load((folder / "agent-evolve.yaml").read_text())
    assert manifest["problem"]["metrics"] and (folder / "hypotheses.md").exists()


def test_cli_init_and_validate(
    tmp_path: Path, isolated_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["init", BRIEF, "--size", "quick", "--no-web", "--seed", "5"]) == 0
    runs = list((isolated_home / "runs").iterdir())
    assert len(runs) == 1 and (runs[0] / "status.json").exists()
    manifest = tmp_path / "brainswarm.yaml"
    manifest.write_text(yaml.safe_dump({"brief": BRIEF, "size": "deep", "exploration": "wild"}))
    assert cli.main(["validate", str(manifest)]) == 0
    assert "deep/wild" in capsys.readouterr().out


def test_fixable_gate_citations_do_not_remove_ideas_from_finals(tmp_path: Path) -> None:
    # Regression: gates.json lists fixable ideas too; only "barred" ones may be excluded.
    import tests.fake_agents as fakes

    fakes.GATE_CITATIONS["critique"] = "trades_daily"
    try:
        run = new_run(tmp_path)
        drive(run)
    finally:
        fakes.GATE_CITATIONS.clear()
    gates = run.read("data", "gates.json")
    assert "fixable" in gates.values()
    barred = {k for k, v in gates.items() if v == "barred"}
    finalists = run.read("data", "final.json")["ids"]
    assert finalists and not {f.split("-")[0] for f in finalists} & barred
    fixable_developed = [
        k
        for k, v in gates.items()
        if v == "fixable" and f"{k}-v2" in run.read("data", "cards.json")
    ]
    assert all(f"{k}-v2" in finalists for k in fixable_developed)


def test_replay_until_branches_a_live_run(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    drive(run)
    branch = cli.replay(run.root, tmp_path / "branch", until="finals")
    assert branch.status["phase"] == "finals" and not branch.exists("data", "matches.json")
    drive(branch)  # new agents finish the branch
    assert branch.status["phase"] == "done"
    assert branch.read("data", "final.json")["ids"] == run.read("data", "final.json")["ids"]
    # Regression: a second branch must not import the first branch's finalists as champions.
    # (Renamed, as branches kept side by side are: the library skips entries whose run folder
    # has the current run's name, which hid the collision while both kept the recorded name.)
    second = cli.replay(run.root, tmp_path / "branch2", until="finals")
    second = Run(second.root.rename(second.root.with_name("second-branch")))
    drive(second)
    assert second.read("data", "finalists.json") == run.read("data", "finalists.json")


def test_judge_verdicts_name_winner_and_criterion(tmp_path: Path) -> None:
    run = new_run(tmp_path)
    branch_root = tmp_path / "b"
    drive(run)
    branch = cli.replay(run.root, branch_root, until="finals")
    step = pipeline.next_step(branch)
    d = pipeline.Dispatch(**branch.status["dispatches"][0])
    batch = next(b for b in branch.read("data", "judge_batches.json") if b["dispatch_id"] == d.id)
    a, b = batch["pairs"][0]
    pid = f"{d.id}-01"
    good = {"pair_id": pid, "strengths": {a: "x", b: "y"}, "winner": b, "criterion": "growth"}
    rest = [
        {"pair_id": f"{d.id}-{i + 1:02d}", "preferred": "first"}  # legacy format still accepted
        for i in range(1, len(batch["pairs"]))
    ]
    assert pipeline.check_judges(branch, d, {"verdicts": [good, *rest]}) == []
    for bad, why in (
        ({**good, "winner": "first"}, "winner must be"),
        ({**good, "criterion": "trades_daily"}, "criterion must be"),  # a gate, not judged
        ({**good, "strengths": {a: "x"}}, "strengths must"),
    ):
        problems = pipeline.check_judges(branch, d, {"verdicts": [bad, *rest]})
        assert any(why in p for p in problems), (bad, problems)
    task = branch.path("tasks", "finals", f"{d.id}.md").read_text()
    assert step["phase"] == "finals" and f"**{a}** vs **{b}**" in task and "first**" not in task


def test_rebuilt_report_does_not_repeat_limitations(tmp_path: Path) -> None:
    # Regression: the digest re-collected its own Limitations line on every rebuild.
    from agent_brainswarm import report

    run = new_run(tmp_path)
    drive(run)
    pipeline._log(run, "critique", ["generic filter: 3 failed the substitution test"])
    for _ in range(3):
        pipeline._log(run, "report", report.build(run))
    digest = run.path("digest.txt").read_text()
    assert digest.count("Limitations:") == 1
    assert digest.count("3 failed the substitution test") == 1
