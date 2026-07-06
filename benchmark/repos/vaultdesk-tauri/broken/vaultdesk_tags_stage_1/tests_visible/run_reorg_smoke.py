#!/usr/bin/env python3
"""Visible reorg-smoke wrapper for the VaultDesk frontend.

Locates a Node interpreter and runs the JavaScript reorg smoke runner, relaying
its stdout and exit code. Paths are resolved relative to this file so the wrapper
keeps working after the workspace is copied to a sandbox.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
RUNNER = HERE.parent / "src" / "tests_visible" / "run_reorg_smoke.js"


def _find_node() -> str:
    candidates = [
        os.environ.get("NODE"),
        shutil.which("node"),
        r"C:\Program Files\nodejs\node.exe",
    ]
    for c in candidates:
        if c and (pathlib.Path(c).exists() or shutil.which(c)):
            return c
    sys.exit(2)


def main() -> int:
    node = _find_node()
    if not RUNNER.exists():
        sys.stderr.write(f"reorg smoke runner not found at {RUNNER}\n")
        return 2
    proc = subprocess.run([node, str(RUNNER)], capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
