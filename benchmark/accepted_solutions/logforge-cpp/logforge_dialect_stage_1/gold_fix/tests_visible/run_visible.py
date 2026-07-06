#!/usr/bin/env python3
"""Visible smoke tests for logforge.

Run from the project root:  python tests_visible/run_visible.py

Compiles the library sources together with tests_visible/visible_main.cpp using
the C++ toolchain and runs the resulting binary. Exits with the binary's code.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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
    cxx = find_cxx()
    sources = sorted(glob.glob(str(ROOT / "src" / "*.cpp")))
    sources.append(str(ROOT / "tests_visible" / "visible_main.cpp"))

    tmp = Path(tempfile.mkdtemp(prefix="tb_logforge_visible_"))
    try:
        exe = tmp / ("visible.exe" if os.name == "nt" else "visible")
        compile_cmd = [cxx, "-std=c++17", "-static", "-O0",
                       "-I", str(ROOT / "include"), *sources, "-o", str(exe)]
        cp = subprocess.run(compile_cmd)
        if cp.returncode != 0:
            return cp.returncode
        return subprocess.run([str(exe)]).returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
