import os, json, subprocess, pathlib, shutil, pytest

HERE = pathlib.Path(__file__).resolve().parent
CHECKS = [
    "files_module_canonical",
    "search_module_canonical",
    "settings_module_canonical",
    "notes_module_canonical",
    "vault_state_canonical",
    "search_state_canonical",
    "settings_state_canonical",
]
_R = {}


def _node():
    for c in (os.environ.get("NODE"), "node", r"C:\Program Files\nodejs\node.exe"):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("node not found")


def _run_node(ws):
    p = subprocess.run(
        [_node(), str(HERE / "harness.mjs")],
        env={**os.environ, "TOKENBENCH_WORKSPACE": ws},
        capture_output=True,
        text=True,
        timeout=120,
    )
    line = [l for l in (p.stdout or "").splitlines() if l.strip().startswith("{")]
    assert line, f"node harness no json. stdout={p.stdout[-800:]} stderr={p.stderr[-1000:]}"
    return json.loads(line[-1])


def setup_module(m):
    ws = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    assert ws, "TOKENBENCH_WORKSPACE not set"
    _R.update(_run_node(ws))


@pytest.mark.parametrize("name", CHECKS)
def test_check(name):
    assert _R.get(name) is True, f"{name}={_R.get(name)!r}"
