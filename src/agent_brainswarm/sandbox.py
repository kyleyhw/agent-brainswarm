"""Sandboxed scratch code for generators and workshop agents (DESIGN.md §12).

A script runs in a Docker container with no network, no package
installation (the image is fixed), limited CPU, memory, processes and wall
time, no environment variables from the host, and a writable scratch
folder as its only writable mount. An optional data folder (e.g. price
history fetched once before the run) is mounted read-only.

Results are sanity checks, never evidence that an idea works.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
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
    script: Path,
    scratch: Path,
    data: Path | None,
    image: str = DEFAULT_IMAGE,
    name: str = "brainswarm-sandbox",
) -> list[str]:
    """The exact docker command (exposed for tests and audit)."""
    cmd = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
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
        # Run as the host user so the scratch mount is writable (the image's own user is
        # uid 1000, which cannot write a folder the host user owns); HOME must be writable.
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--env",
        "HOME=/tmp",
        "-v",
        f"{scratch.resolve()}:/work:rw",
        "-v",
        f"{script.resolve()}:/work/script.py:ro",
        "-w",
        "/work",
    ]
    if data is not None:
        cmd += ["-v", f"{data.resolve()}:/data:ro"]
    # --entrypoint skips the image's notebook start script (which fails on a read-only root
    # when the uid is 0); -u: unbuffered, so output before a memory-limit kill (137) is kept.
    return [*cmd, "--entrypoint", "python", image, "-u", "/work/script.py"]


def run(
    script: Path, scratch: Path, data: Path | None = None, image: str = DEFAULT_IMAGE
) -> Result:
    """Run ``script`` in the sandbox; raise SandboxUnavailable if Docker is not usable."""
    ok, reason = available()
    if not ok:
        raise SandboxUnavailable(reason)
    scratch.mkdir(parents=True, exist_ok=True)
    name = f"brainswarm-sandbox-{uuid.uuid4().hex[:12]}"
    try:
        proc = subprocess.run(
            command(script, scratch, data, image, name),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
    except subprocess.TimeoutExpired as err:
        # The timeout kills only the docker client; the container would keep running.
        subprocess.run(["docker", "kill", name], capture_output=True, check=False)
        return Result(-1, _text(err.stdout), _text(err.stderr), True)
    return Result(proc.returncode, proc.stdout, proc.stderr, False)


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""
