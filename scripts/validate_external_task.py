"""Validate an external-repo bug-fix task: gold passes, broken fails, accepted passes.

Materializes three workspaces from the pinned cache clone:
  - gold     = clone (pinned commit, no patch)            -> hidden must PASS (1.0)
  - broken   = clone + defect.patch                       -> hidden must FAIL (< gate)
  - accepted = clone + defect.patch + accepted_solution.patch -> hidden must PASS (>= gate)

Hidden commands are run from the PROJECT ROOT (base_dir) with TOKENBENCH_WORKSPACE
and PYTHONPATH pointed at the materialized workspace -- matching the real harness.
The validator parses the `TOKENBENCH_CHECKS passed=<n> total=<n>` marker so it
reports a per-check pass-rate, and also falls back to exit-code pass/fail.

Usage:
  python scripts/validate_external_task.py <path/to/manifest.json>
      [--setup "<shell cmd run inside each workspace before hidden tests>"]
      [--gate 0.9] [--keep] [--timeout 300]

Examples:
  python scripts/validate_external_task.py benchmark/external_repos/<name>/tasks/<task>/manifest.json --setup "pip install -e . -q"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKS_RE = re.compile(r"TOKENBENCH_CHECKS\s+passed=(\d+)\s+total=(\d+)", re.IGNORECASE)

# Directories never copied into a workspace. `git apply` does not require a git
# repo for cleanly-authored patches, so we drop .git (huge for some repos) too.
JUNK = {".git", ".github", "bin", "obj", "node_modules", ".tox", ".venv", "venv",
        "__pycache__", ".pytest_cache", "dist", "build", ".mypy_cache",
        ".nyc_output", "coverage", ".tap", ".cache"}


def _ignore(_d, names):
    return {n for n in names if n in JUNK}


def find_project_root(start: Path) -> Path:
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / "tokenbench").is_dir() and (cand / "benchmark").is_dir():
            return cand
    return Path.cwd()


def git_apply(patch: Path, workspace: Path) -> tuple[bool, str]:
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)],
                       cwd=workspace, capture_output=True, text=True)
    if r.returncode == 0:
        return True, ""
    r2 = subprocess.run(["git", "apply", "-3", "--whitespace=nowarn", str(patch)],
                        cwd=workspace, capture_output=True, text=True)
    if r2.returncode == 0:
        return True, ""
    return False, r.stderr + r2.stderr


def parse_checks(text: str):
    matches = list(CHECKS_RE.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    passed, total = int(m.group(1)), int(m.group(2))
    if total < passed:
        total = passed
    return passed, total


def run_variant(name, clone_dir, task_dir, patches, manifest, root, setup, timeout, keep):
    ws = Path(tempfile.mkdtemp(prefix=f"tbval_{name}_"))
    ws_repo = ws / "workspace"
    shutil.copytree(clone_dir, ws_repo, ignore=_ignore)

    for patch_name in patches:
        patch = task_dir / patch_name
        if not patch.exists():
            return {"variant": name, "error": f"missing patch {patch_name}"}
        ok, err = git_apply(patch, ws_repo)
        if not ok:
            return {"variant": name, "error": f"git apply {patch_name} failed:\n{err[:1500]}"}

    # copy visible tests in (harmless; some hidden tests share helpers)
    vis = task_dir / "visible_tests"
    if vis.exists() and any(vis.iterdir()):
        shutil.copytree(vis, ws_repo / "tests_visible", dirs_exist_ok=True)

    env = dict(os.environ)
    env["TOKENBENCH_WORKSPACE"] = str(ws_repo)
    env["PYTHONPATH"] = str(ws_repo) + os.pathsep + env.get("PYTHONPATH", "")

    if setup:
        s = subprocess.run(setup, shell=True, cwd=ws_repo, env=env,
                           capture_output=True, text=True, timeout=timeout)
        if s.returncode != 0:
            if not keep:
                shutil.rmtree(ws, ignore_errors=True)
            return {"variant": name, "error": f"setup failed (rc={s.returncode}):\n{(s.stdout + s.stderr)[-1500:]}"}

    out_all = ""
    rc_all = 0
    for cmd in manifest["hidden_commands"]:
        # hidden commands are written project-root-relative -> run from root
        r = subprocess.run(cmd, shell=True, cwd=root, env=env,
                           capture_output=True, text=True, timeout=timeout)
        out_all += f"$ {cmd}\n{r.stdout}\n{r.stderr}\n"
        rc_all = rc_all or r.returncode

    if not keep:
        shutil.rmtree(ws, ignore_errors=True)

    checks = parse_checks(out_all)
    res = {"variant": name, "exit_code": rc_all, "workspace": str(ws_repo) if keep else None,
           "tail": out_all[-700:]}
    if checks:
        passed, total = checks
        res["passed"] = passed
        res["total"] = total
        res["pass_rate"] = round(passed / total, 4) if total else 0.0
    else:
        res["pass_rate"] = 1.0 if rc_all == 0 else 0.0
        res["note"] = "no TOKENBENCH_CHECKS marker; using exit code"
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--setup", default="")
    ap.add_argument("--gate", type=float, default=0.9)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--skip-gold", action="store_true",
                    help="extension-bug tasks: the defect.patch ADDS a bespoke buggy "
                         "extension (not in upstream), so pristine 'gold' has no feature "
                         "and is not a passing reference. Only require broken<gate and "
                         "accepted==1.0.")
    args = ap.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    task_dir = manifest_path.parent
    root = find_project_root(manifest_path)

    source_path = root / manifest["source_ref"]
    clone_dir = source_path.parent / "cache" / ".git_clone"
    if not clone_dir.exists():
        print(f"ERROR: clone not found: {clone_dir}")
        sys.exit(2)

    staged = not (task_dir / "defect.patch").exists()
    if staged:
        # Staged implementation task: no defect. Pristine repo lacks the feature
        # (baseline must FAIL); the reference solution adds it (accepted PASSES).
        variants = [
            ("baseline", []),
            ("accepted", ["accepted_solution.patch"]),
        ]
    else:
        variants = [] if args.skip_gold else [("gold", [])]
        variants.append(("broken", ["defect.patch"]))
        if (task_dir / "accepted_solution.patch").exists():
            variants.append(("accepted", ["defect.patch", "accepted_solution.patch"]))

    print(f"== {manifest['task_id']} ==  ({'staged' if staged else 'bugfix'}, gate={args.gate})")
    results = []
    for name, patches in variants:
        res = run_variant(name, clone_dir, task_dir, patches, manifest, root,
                          args.setup, args.timeout, args.keep)
        results.append(res)
        if "error" in res:
            print(f"  {name:9s} ERROR: {res['error']}")
        else:
            pr = res["pass_rate"]
            cnt = f"{res.get('passed','?')}/{res.get('total','?')}"
            print(f"  {name:9s} pass_rate={pr:.3f} checks={cnt} exit={res['exit_code']}")

    # verdict
    by = {r["variant"]: r for r in results}
    ok = True
    if staged:
        if "error" in by.get("baseline", {}) or by.get("baseline", {}).get("pass_rate", 1) >= args.gate:
            ok = False
            print(f"  FAIL: baseline (no feature) must be < gate ({args.gate})")
        if "error" in by.get("accepted", {}) or by.get("accepted", {}).get("pass_rate", 0) < 1.0:
            ok = False
            print("  FAIL: accepted (reference impl) must pass 1.0")
    else:
        if not args.skip_gold and ("error" in by.get("gold", {}) or by.get("gold", {}).get("pass_rate", 0) < 1.0):
            ok = False
            print("  FAIL: gold must pass 1.0")
        if "error" in by.get("broken", {}) or by.get("broken", {}).get("pass_rate", 1) >= args.gate:
            ok = False
            print(f"  FAIL: broken must be < gate ({args.gate})")
        if "accepted" in by:
            if "error" in by["accepted"] or by["accepted"].get("pass_rate", 0) < args.gate:
                ok = False
                print(f"  FAIL: accepted must be >= gate ({args.gate})")
    print("  VERDICT:", "PASS" if ok else "NEEDS WORK")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
