"""Command-line interface: the referee's only way to touch run state.

brainswarm init "<brief>" [--size S] [--exploration E] [--here] [--no-web] [--checkpoint]
brainswarm init --manifest brainswarm.yaml
brainswarm next <run>        what to do now (JSON)
brainswarm ingest <run>      validate agent outputs, advance
brainswarm freeze <run>      freeze rubric_draft.json
brainswarm status <run>      compact digest (use after any compaction)
brainswarm resume <run>      leave the opt-in checkpoint
brainswarm report <run>      re-render the report
brainswarm export <run> [--top N | --idea ID] [--out DIR]
brainswarm feedback <run> <idea> <starred|pursued|exported|worked|failed> [--note ...]
brainswarm validate <brainswarm.yaml>
brainswarm replay <recorded-run> [--into DIR]
brainswarm sandbox run <script.py> [--data DIR] [--scratch DIR]
brainswarm guard             PreToolUse hook for role agents (reads JSON on stdin)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from agent_brainswarm import export, guard, library, pipeline, report, sandbox
from agent_brainswarm.config import build_config, config_to_dict, load_manifest
from agent_brainswarm.models import SchemaError
from agent_brainswarm.state import (
    Run,
    ensure_gitignored,
    home,
    is_ephemeral,
    new_run_id,
    resolve_run,
)

SUBCOMMANDS: tuple[str, ...] = (
    "init",
    "next",
    "ingest",
    "freeze",
    "status",
    "resume",
    "report",
    "export",
    "feedback",
    "validate",
    "replay",
    "sandbox",
    "guard",
)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2) if not isinstance(obj, str) else obj)


def create_run(brief: str, config_dict: dict[str, Any], parent: Path, project: str) -> Run:
    """Make a run folder with brief, config, and initial status."""
    run = Run(parent / new_run_id(int(config_dict["seed"])))
    run.root.mkdir(parents=True, exist_ok=False)
    run.path("brief.md").write_text(brief.strip() + "\n")
    run.write(config_dict, "config.json")
    run.write({**pipeline.init_status(), "project": project}, "status.json")
    return run


def cmd_init(args: argparse.Namespace) -> int:
    overrides: dict[str, Any] = {}
    if args.no_web:
        overrides["web"] = False
    if args.checkpoint:
        overrides["checkpoint"] = True
    if args.manifest:
        brief, config = load_manifest(Path(args.manifest))
        if overrides:
            config = build_config(config.size, config.exploration, overrides, config.seed)
    else:
        if not args.brief:
            print("init needs a brief or --manifest", file=sys.stderr)
            return 2
        brief = args.brief
        config = build_config(args.size, args.exploration, overrides, args.seed)
    if args.here:
        parent = Path.cwd() / "brainswarm-state"
        if ensure_gitignored(Path.cwd()):
            print("added brainswarm-state/ to .gitignore")
    else:
        parent = home() / "runs"
    project = args.project or Path.cwd().name
    run = create_run(brief, config_to_dict(config), parent, project)
    print(f"run: {run.root}")
    if is_ephemeral() and not args.here:
        print(
            "warning: this environment is ephemeral; the run folder and idea library are lost when it is reclaimed"
        )
    print(f"next: write {run.path('rubric_draft.json')} then run: brainswarm next {run.root}")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    _print(pipeline.next_step(resolve_run(args.run)))
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    try:
        _print("\n".join(pipeline.ingest(resolve_run(args.run))))
    except pipeline.PhaseError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    try:
        print(f"rubric frozen: sha256 {pipeline.freeze(resolve_run(args.run))}")
    except SchemaError as err:
        print("rubric rejected:\n" + "\n".join(f"- {p}" for p in err.problems), file=sys.stderr)
        return 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    run = resolve_run(args.run)
    print("\n".join(pipeline.status_lines(run)))
    if run.exists("digest.txt"):
        print(run.path("digest.txt").read_text())
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    pipeline.resume(resolve_run(args.run))
    print("checkpoint cleared; run: brainswarm next")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    print("\n".join(report.build(resolve_run(args.run))))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    run = resolve_run(args.run)
    out = Path(args.out or Path.cwd() / "brainswarm-export" / run.root.name)
    ideas = [args.idea] if args.idea else export.top_families(run)[: args.top]
    for idea in ideas:
        print(export.bundle(run, idea, out))
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    run = resolve_run(args.run)
    library.record_feedback(run, args.idea, args.status, args.note or "")
    print(f"recorded: {args.idea} {args.status}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        brief, config = load_manifest(Path(args.manifest))
    except SchemaError as err:
        print("\n".join(f"- {p}" for p in err.problems), file=sys.stderr)
        return 1
    print(
        f"ok: {config.size}/{config.exploration}, {config.generators} generators; brief: {brief[:60]}"
    )
    return 0


def replay(recorded: Path, into: Path) -> Run:
    """Re-run the code layer over a recorded run's agent outputs (zero tokens)."""
    source = Run(recorded)
    config = source.read("config.json")
    run = Run(into / source.root.name)
    if run.root.exists():
        shutil.rmtree(run.root)
    run.root.mkdir(parents=True)
    run.path("brief.md").write_text(source.brief)
    run.write(config, "config.json")
    run.write({**pipeline.init_status(), "project": f"replay-{source.root.name}"}, "status.json")
    shutil.copy(source.path("rubric_draft.json"), run.path("rubric_draft.json"))
    while True:
        step = pipeline.next_step(run)
        if step["action"] == "done":
            return run
        if step["phase"] == "freeze":
            final = source.path("rubric.json")
            shutil.copy(
                final if final.exists() else source.path("rubric_draft.json"),
                run.path("rubric_draft.json"),
            )
            pipeline.freeze(run)
            continue
        if step["action"] == "referee":
            if step["phase"] == "checkpoint":
                pipeline.resume(run)
                continue
            raise RuntimeError(f"replay cannot perform referee action in phase {step['phase']}")
        for d in step["dispatches"]:
            src = source.path("out", step["phase"], f"{d['id']}.json")
            dst = run.path("out", step["phase"], f"{d['id']}.json")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy(src, dst)
        pipeline.ingest(run)


def cmd_replay(args: argparse.Namespace) -> int:
    run = replay(Path(args.recorded), Path(args.into or Path.cwd() / "brainswarm-replay"))
    print(run.path("digest.txt").read_text())
    return 0


def cmd_sandbox(args: argparse.Namespace) -> int:
    try:
        result = sandbox.run(
            Path(args.script), Path(args.scratch), Path(args.data) if args.data else None
        )
    except sandbox.SandboxUnavailable as err:
        print(f"sandbox unavailable ({err}); run no code and say so in your card", file=sys.stderr)
        return 3
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return 124 if result.timed_out else result.returncode


def cmd_guard(args: argparse.Namespace) -> int:
    return guard.main()


def parser() -> argparse.ArgumentParser:
    """Argument parser for all subcommands."""
    p = argparse.ArgumentParser(
        prog="brainswarm", description="Generate ideas at scale and rank them honestly."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init")
    s.add_argument("brief", nargs="?")
    s.add_argument("--manifest")
    s.add_argument("--size", default="standard", choices=["quick", "standard", "deep"])
    s.add_argument(
        "--exploration", default="balanced", choices=["conservative", "balanced", "wild"]
    )
    s.add_argument("--here", action="store_true")
    s.add_argument("--no-web", action="store_true")
    s.add_argument("--checkpoint", action="store_true")
    s.add_argument("--project")
    s.add_argument("--seed", type=int)
    s.set_defaults(func=cmd_init)

    for name, func in (
        ("next", cmd_next),
        ("ingest", cmd_ingest),
        ("freeze", cmd_freeze),
        ("status", cmd_status),
        ("resume", cmd_resume),
        ("report", cmd_report),
    ):
        s = sub.add_parser(name)
        s.add_argument("run")
        s.set_defaults(func=func)

    s = sub.add_parser("export")
    s.add_argument("run")
    s.add_argument("--top", type=int, default=5)
    s.add_argument("--idea")
    s.add_argument("--out")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("feedback")
    s.add_argument("run")
    s.add_argument("idea")
    s.add_argument("status", choices=["starred", "pursued", "exported", "worked", "failed"])
    s.add_argument("--note")
    s.set_defaults(func=cmd_feedback)

    s = sub.add_parser("validate")
    s.add_argument("manifest")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("replay")
    s.add_argument("recorded")
    s.add_argument("--into")
    s.set_defaults(func=cmd_replay)

    s = sub.add_parser("sandbox")
    s.add_argument("action", choices=["run"])
    s.add_argument("script")
    s.add_argument("--data")
    s.add_argument("--scratch", default="./sandbox-scratch")
    s.set_defaults(func=cmd_sandbox)

    s = sub.add_parser("guard")
    s.set_defaults(func=cmd_guard)
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parser().parse_args(sys.argv[1:] if argv is None else argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
