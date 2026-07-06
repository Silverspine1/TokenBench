"""Generic hidden-test driver for mvm (Go) tasks.

A task's hidden_command invokes:
    python benchmark/external_repos/mvm/hidden_driver.py <task>/hidden_tests

This copies every *.go file from <task>/hidden_tests/ into a `tbhidden/`
package inside the materialized workspace (TOKENBENCH_WORKSPACE), then runs
`go run ./tbhidden`. The harness program (package main) constructs an mvm
interpreter against the workspace's own source, runs guest Go programs, asserts
their output, and prints `TOKENBENCH_CHECKS passed=<n> total=<n>`.

The driver streams the harness stdout/stderr through and exits with its code, so
both the validator and the real scorer can parse the marker and the exit code.

Go is forced onto PATH (the harness needs the `go` toolchain) regardless of the
caller's environment.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

GO_BIN = r"C:\Program Files\Go\bin"


def _resolve(name: str, path: str) -> str:
    """Resolve an executable on the given PATH (Windows needs the .exe)."""
    found = shutil.which(name, path=path)
    if found:
        return found
    cand = Path(GO_BIN) / (name + ".exe")
    return str(cand) if cand.exists() else name


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: hidden_driver.py <hidden_tests_dir>", file=sys.stderr)
        return 2
    hidden_dir = Path(sys.argv[1]).resolve()
    if not hidden_dir.is_dir():
        print(f"hidden_tests dir not found: {hidden_dir}", file=sys.stderr)
        return 2

    ws = os.environ.get("TOKENBENCH_WORKSPACE", "")
    if not ws:
        print("TOKENBENCH_WORKSPACE not set", file=sys.stderr)
        return 2
    ws_path = Path(ws).resolve()
    if not (ws_path / "go.mod").exists():
        print(f"workspace has no go.mod: {ws_path}", file=sys.stderr)
        return 2

    # Stage the harness as a fresh tbhidden/ package inside the module.
    dst = ws_path / "tbhidden"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    go_files = sorted(hidden_dir.glob("*.go"))
    if not go_files:
        print(f"no *.go harness files in {hidden_dir}", file=sys.stderr)
        return 2
    for f in go_files:
        shutil.copy2(f, dst / f.name)

    env = dict(os.environ)
    if GO_BIN.lower() not in env.get("PATH", "").lower():
        env["PATH"] = GO_BIN + os.pathsep + env.get("PATH", "")

    go_exe = _resolve("go", env["PATH"])
    try:
        r = subprocess.run(
            [go_exe, "run", "./tbhidden"],
            cwd=str(ws_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=240,
        )
    except subprocess.TimeoutExpired:
        print("TOKENBENCH_CHECKS passed=0 total=1")
        print("hidden harness timed out", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(dst, ignore_errors=True)

    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
