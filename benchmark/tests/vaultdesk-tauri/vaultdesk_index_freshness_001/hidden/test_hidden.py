import os, json, subprocess, pathlib, shutil, tempfile, sys, hashlib, pytest

HERE = pathlib.Path(__file__).resolve().parent
CHECKS = [
    "create_indexed",
    "update_reflected",
    "delete_disappears",
    "rename_path_updated",
    "rescan_rebuilds",
    "tokenizer_lowercases",
]
USE_NODE = False
CACHE = pathlib.Path(os.environ.get("TEMP", "/tmp")) / "vaultdesk_target_cache"
_R = {}
MINGW = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe", "mingw64", "bin")


def _cargo():
    for c in (os.environ.get("CARGO"), os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "cargo.exe"), "cargo"):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("cargo not found")


def _node():
    for c in (os.environ.get("NODE"), "node", r"C:\Program Files\nodejs\node.exe"):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("node not found")


def _run_rust(ws):
    # Use a stable, identity-keyed working dir and a dedicated CARGO_TARGET_DIR so
    # cargo fingerprints stay consistent across runs (warm incremental builds) and
    # are never shared between distinct source trees (no stale rlib reuse between
    # gold and broken snapshots).
    key = hashlib.sha1((str(HERE) + "|" + str(pathlib.Path(ws).resolve())).encode()).hexdigest()[:16]
    base = pathlib.Path(os.environ.get("TEMP", "/tmp")) / ("vd_work_" + key)
    srctauri = base / "src-tauri"
    if srctauri.exists():
        shutil.rmtree(srctauri, ignore_errors=True)
    shutil.copytree(pathlib.Path(ws) / "src-tauri", srctauri,
                    ignore=shutil.ignore_patterns("target", "node_modules", ".git"))
    (srctauri / "tests").mkdir(exist_ok=True)
    shutil.copy(HERE / "vd_harness.rs", srctauri / "tests" / "vd_harness.rs")
    out = srctauri / "vd_out.json"
    target = pathlib.Path(os.environ.get("TEMP", "/tmp")) / ("vd_target_" + key)
    env = {**os.environ, "PATH": MINGW + os.pathsep + os.environ.get("PATH", ""),
           "CARGO_TARGET_DIR": str(target), "VD_OUT": str(out)}
    p = subprocess.run([_cargo(), "test", "--test", "vd_harness", "--", "--nocapture"],
                       cwd=str(srctauri), env=env, capture_output=True, text=True, timeout=110)
    assert out.exists(), f"rust harness produced no output. stdout={p.stdout[-1500:]} stderr={p.stderr[-1500:]}"
    return json.loads(out.read_text())


def _run_node(ws):
    p = subprocess.run([_node(), str(HERE / "harness.mjs")],
                       env={**os.environ, "TOKENBENCH_WORKSPACE": ws},
                       capture_output=True, text=True, timeout=60)
    line = [l for l in (p.stdout or "").splitlines() if l.strip().startswith("{")]
    assert line, f"node harness no json. stderr={p.stderr[-1000:]}"
    return json.loads(line[-1])


def setup_module(m):
    ws = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    assert ws
    _R.update(_run_rust(ws))
    if USE_NODE:
        _R.update(_run_node(ws))


@pytest.mark.parametrize("name", CHECKS)
def test_check(name):
    assert _R.get(name) is True, f"{name}={_R.get(name)!r}"
