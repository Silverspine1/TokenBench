"""Generic hidden-test driver for SharpTS (C#) tasks.

A task's hidden_command invokes:
    python benchmark/external_repos/sharpts/hidden_driver.py <task>/hidden_tests

Steps:
  1. Build the workspace's SharpTS.csproj in Release (rebuilds the agent's edited
     source). MinVerVersionOverride is forced so the build never depends on git
     history (the real harness strips .git from the workspace).
  2. For each case in <hidden_tests>/cases.json, run the named TypeScript program
     (a .ts file in <hidden_tests>/) through the freshly built CLI and check its
     stdout / exit behavior.
  3. Print `TOKENBENCH_CHECKS passed=<n> total=<n>` and exit 0 iff all passed.

cases.json schema: a JSON list of objects, each:
    {
      "name": "human label",
      "program": "foo.ts",            # a .ts file living in hidden_tests/
      "args": ["optional","argv"],     # optional program args
      "exact": "full expected stdout (trimmed)",     # optional
      "contains": ["substr1","substr2"],             # optional, all must appear
      "not_contains": ["bad"],                        # optional, none may appear
      "exit_nonzero": false             # optional; true => program must error out
    }
Each object is ONE check (one unit toward passed/total).

Dotnet is forced onto PATH.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

DOTNET_DIR = r"C:\Program Files\dotnet"


def build(ws: Path, env: dict) -> tuple[bool, str]:
    r = subprocess.run(
        ["dotnet", "build", "SharpTS.csproj", "-c", "Release",
         "-p:MinVerVersionOverride=0.0.0-tb", "--nologo", "-v", "quiet"],
        cwd=str(ws), env=env, capture_output=True, text=True, timeout=600,
    )
    return r.returncode == 0, (r.stdout + r.stderr)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: hidden_driver.py <hidden_tests_dir>", file=sys.stderr)
        return 2
    hidden_dir = Path(sys.argv[1]).resolve()
    cases_file = hidden_dir / "cases.json"
    if not cases_file.exists():
        print(f"cases.json not found in {hidden_dir}", file=sys.stderr)
        return 2
    cases = json.loads(cases_file.read_text(encoding="utf-8"))

    ws = os.environ.get("TOKENBENCH_WORKSPACE", "")
    if not ws:
        print("TOKENBENCH_WORKSPACE not set", file=sys.stderr)
        return 2
    ws_path = Path(ws).resolve()

    env = dict(os.environ)
    if DOTNET_DIR.lower() not in env.get("PATH", "").lower():
        env["PATH"] = DOTNET_DIR + os.pathsep + env.get("PATH", "")
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"

    ok, log = build(ws_path, env)
    if not ok:
        print("TOKENBENCH_CHECKS passed=0 total=%d" % max(1, len(cases)))
        print("BUILD FAILED:\n" + log[-2000:], file=sys.stderr)
        return 1

    dll = ws_path / "bin" / "Release" / "net10.0" / "SharpTS.dll"
    if not dll.exists():
        print("TOKENBENCH_CHECKS passed=0 total=%d" % max(1, len(cases)))
        print(f"built DLL not found at {dll}", file=sys.stderr)
        return 1

    passed = 0
    total = 0
    for c in cases:
        total += 1
        name = c.get("name", c.get("program", f"case{total}"))
        prog = hidden_dir / c["program"]
        if not prog.exists():
            print(f"not ok - {name}: program {c['program']} missing")
            continue
        argv = ["dotnet", str(dll), str(prog)] + list(c.get("args", []))
        try:
            r = subprocess.run(argv, cwd=str(ws_path), env=env,
                               capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            print(f"not ok - {name}: timeout")
            continue
        out = r.stdout.strip()
        fail = None
        if c.get("exit_nonzero"):
            if r.returncode == 0:
                fail = "expected nonzero exit (program error) but it succeeded"
        else:
            if r.returncode != 0:
                fail = f"unexpected nonzero exit ({r.returncode}); stderr={r.stderr.strip()[:200]}"
        if fail is None and "exact" in c:
            if out != c["exact"].strip():
                fail = f"stdout != exact; got {out!r}"
        if fail is None and "contains" in c:
            for sub in c["contains"]:
                if sub not in r.stdout:
                    fail = f"stdout missing {sub!r}; got {out!r}"
                    break
        if fail is None and "not_contains" in c:
            for sub in c["not_contains"]:
                if sub in r.stdout:
                    fail = f"stdout unexpectedly contains {sub!r}; got {out!r}"
                    break
        if fail is None:
            passed += 1
        else:
            print(f"not ok - {name}: {fail}")

    print(f"TOKENBENCH_CHECKS passed={passed} total={total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
