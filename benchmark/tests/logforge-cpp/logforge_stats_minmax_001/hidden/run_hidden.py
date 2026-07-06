#!/usr/bin/env python3
"""Hidden-test driver for logforge_stats_minmax_001.

The candidate workspace is copied to an isolated temp directory, then the hidden
test (test_main.cpp) is compiled together with the candidate's library sources
and run. The driver exits with the test binary's exit code. Nothing is written
back into the candidate workspace.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_cxx() -> str:
    env_cxx = os.environ.get("CXX")
    if env_cxx and (shutil.which(env_cxx) or os.path.exists(env_cxx)):
        return env_cxx
    for name in ("g++", "c++", "clang++"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        "/usr/bin/g++",
        "/usr/local/bin/g++",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    print("no C++ compiler (g++/c++/clang++) found", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    workspace = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    if not workspace:
        print("TOKENBENCH_WORKSPACE is not set", file=sys.stderr)
        return 2
    workspace = Path(workspace)
    if not (workspace / "include" / "logforge").exists():
        print(f"no logforge include tree under workspace: {workspace}", file=sys.stderr)
        return 2

    cxx = find_cxx()
    tmp = Path(tempfile.mkdtemp(prefix="tb_logforge_hidden_"))
    try:
        ws = tmp / "ws"
        shutil.copytree(workspace, ws, ignore=shutil.ignore_patterns(".git", "*.exe", "build"))
        sources = sorted(glob.glob(str(ws / "src" / "*.cpp")))
        if not sources:
            print("no library sources found under src/", file=sys.stderr)
            return 2
        sources.append(str(HERE / "test_main.cpp"))

        exe = tmp / ("hidden.exe" if os.name == "nt" else "hidden")
        compile_cmd = [cxx, "-std=c++17", "-static", "-O0",
                       "-I", str(ws / "include"), *sources, "-o", str(exe)]
        cp = subprocess.run(compile_cmd)
        if cp.returncode != 0:
            print("hidden test failed to compile against candidate sources", file=sys.stderr)
            return cp.returncode
        return subprocess.run([str(exe)]).returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
