"""Command-line entry point: ``brainswarm validate / report / export / resume / feedback``.

Scaffold only: every subcommand reports that it is not implemented yet.
See docs/DESIGN.md §13.
"""

from __future__ import annotations

import sys

SUBCOMMANDS: tuple[str, ...] = ("validate", "report", "export", "resume", "feedback")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    name = args[0] if args else "(none)"
    print(f"brainswarm {name}: not implemented yet (design phase; see docs/DESIGN.md)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
