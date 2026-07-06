#!/usr/bin/env python3
"""Hidden-test driver for bizflow_report_scope_001.

The candidate workspace is copied to an isolated temp directory, the Go check
program (check.go) is dropped into it as its own package, and `go run` compiles
the check against the candidate's code. The driver exits with the check's exit
code, so a failing assertion fails the hidden test. Nothing is written back into
the candidate workspace.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_go() -> str:
    go = shutil.which("go")
    if go:
        return go
    candidates = [
        os.path.join(os.environ.get("GOROOT", ""), "bin", "go"),
        r"C:\Program Files\Go\bin\go.exe",
        "/usr/local/go/bin/go",
        os.path.expanduser("~/go/bin/go"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    print("go toolchain not found on PATH or in known locations", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    workspace = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    if not workspace:
        print("TOKENBENCH_WORKSPACE is not set", file=sys.stderr)
        return 2
    workspace = Path(workspace)
    if not (workspace / "go.mod").exists():
        print(f"no go.mod under workspace: {workspace}", file=sys.stderr)
        return 2

    go = find_go()
    tmp = Path(tempfile.mkdtemp(prefix="tb_bizflow_hidden_"))
    try:
        ws = tmp / "ws"
        shutil.copytree(
            workspace,
            ws,
            ignore=shutil.ignore_patterns(".git", "*.exe", "*.test"),
        )
        check_pkg = ws / "_hidden_check"
        check_pkg.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / "check.go", check_pkg / "main.go")

        env = dict(os.environ)
        env.setdefault("GOFLAGS", "-mod=mod")
        proc = subprocess.run(
            [go, "run", "./_hidden_check"],
            cwd=str(ws),
            env=env,
        )
        return proc.returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
