import os, json, subprocess, pathlib, shutil, sys, pytest
HERE = pathlib.Path(__file__).resolve().parent
CHECKS = [
    "pause_prevents_due_attempt",
    "resume_restores_due_attempt",
    "failed_attempt_increments_failure_count",
    "retry_is_idempotent",
    "three_failures_pause_schedule",
    "stage1_schedule_behavior_unchanged",
]
_R = {}
def _php():
    cands = [os.environ.get("PHP"), "php", os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "PHP.PHP.8.3_Microsoft.Winget.Source_8wekyb3d8bbwe", "php.exe")]
    for c in cands:
        if not c: continue
        w = shutil.which(c)
        if w: return w
        if pathlib.Path(c).exists(): return c
    raise RuntimeError("php not found")
def setup_module(module):
    ws = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    assert ws, "TOKENBENCH_WORKSPACE not set"
    p = subprocess.run([_php(), str(HERE / "checks.php")], capture_output=True, text=True, env={**os.environ})
    out = (p.stdout or "").strip().splitlines()
    assert out, f"no output from checks.php; stderr={p.stderr[:800]}"
    _R.update(json.loads(out[-1]))
@pytest.mark.parametrize("name", CHECKS)
def test_check(name):
    assert _R.get(name) is True, f"{name} failed (value={_R.get(name)!r})"
