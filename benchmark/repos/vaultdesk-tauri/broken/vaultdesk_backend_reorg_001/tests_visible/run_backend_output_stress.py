#!/usr/bin/env python3
"""Long-output visible check for the VaultDesk backend reorg task.

Builds and runs the `reorg_stress` cargo example, which drives the real backend
(search index, scanner, note store, path safety, settings migration) over a
fixed, hard-coded corpus and prints one stable line per observed result. The
output is deterministic and offline. This wrapper streams that stdout through so
the harness can measure the long-output volume.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE_ROOT = HERE.parent
SRC_TAURI = WORKSPACE_ROOT / "src-tauri"
MINGW = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft", "WinGet", "Packages",
    "BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "mingw64", "bin",
)


def find_cargo() -> str:
    for c in (
        os.environ.get("CARGO"), os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "cargo.exe"), "cargo",
    ):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return shutil.which(c) or c
    return ""


def main() -> int:
    cargo = find_cargo()
    if not cargo:
        sys.stderr.write("cargo not found\n")
        return 2
    if not SRC_TAURI.exists():
        sys.stderr.write(f"src-tauri not found at {SRC_TAURI}\n")
        return 2

    key = hashlib.sha1(str(SRC_TAURI.resolve()).encode()).hexdigest()[:16]
    target = pathlib.Path(os.environ.get("TEMP", "/tmp")) / ("vd_stress_tgt_" + key)
    env = {
        **os.environ,
        "PATH": MINGW + os.pathsep + os.environ.get("PATH", ""),
        "CARGO_TARGET_DIR": str(target),
    }
    proc = subprocess.run(
        [cargo, "run", "--quiet", "--example", "reorg_stress"],
        cwd=str(SRC_TAURI),
        env=env,
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
