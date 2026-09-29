"""Sandboxed scratch code for generators and workshop agents (DESIGN.md §12).

A script runs in a Docker container with no network, no package
installation (the image is fixed), limited CPU, memory, processes and wall
time, no environment variables from the host, and a writable scratch
folder as its only writable mount. An optional data folder (e.g. price
history fetched once before the run) is mounted read-only.

Results are sanity checks, never evidence that an idea works.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# A plain python:3.12 image has no scientific packages and installs are
# blocked, so the default is the official Jupyter scientific-Python image.
DEFAULT_IMAGE = "quay.io/jupyter/scipy-notebook:latest"
TIMEOUT_S = 120  # a sanity check that needs longer is not a quick check
MEMORY = "1g"
CPUS = "1"
PIDS = "128"


class SandboxUnavailable(RuntimeError):
    """Docker is not installed or its daemon is not reachable."""


@dataclass(frozen=True)
class Result:
    """Outcome of one sandboxed run."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def available() -> tuple[bool, str]:
    """Whether a working Docker daemon is reachable, with the reason if not."""
    if not shutil.which("docker"):
        return False, "docker is not installed"
    probe = subprocess.run(["docker", "info"], capture_output=True, text=True, check=False)
    if probe.returncode != 0:
        return False, (probe.stderr.strip().splitlines() or ["docker info failed"])[-1]
    return True, ""


def command(
    script: Path, scratch: Path, data: Path | None, image: str = DEFAULT_IMAGE
) -> list[str]:
    """The exact docker command (exposed for tests and audit)."""
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--memory",
        MEMORY,
        "--cpus",
        CPUS,
        "--pids-limit",
        PIDS,
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=64m",
        "--security-opt",
        "no-new-privileges",
        "--cap-drop",
        "ALL",
        "-v",
        f"{scratch.resolve()}:/work:rw",
        "-v",
        f"{script.resolve()}:/work/script.py:ro",
        "-w",
        "/work",
    ]
    if data is not None:
        cmd += ["-v", f"{data.resolve()}:/data:ro"]
    return [*cmd, image, "python", "/work/script.py"]


def run(
    script: Path, scratch: Path, data: Path | None = None, image: str = DEFAULT_IMAGE
) -> Result:
    """Run ``script`` in the sandbox; raise SandboxUnavailable if Docker is not usable."""
    ok, reason = available()
    if not ok:
        raise SandboxUnavailable(reason)
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            command(script, scratch, data, image),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
    except subprocess.TimeoutExpired as err:
        return Result(-1, str(err.stdout or ""), str(err.stderr or ""), True)
    return Result(proc.returncode, proc.stdout, proc.stderr, False)
