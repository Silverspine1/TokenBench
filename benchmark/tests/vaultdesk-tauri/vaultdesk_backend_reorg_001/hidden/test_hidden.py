import os, json, subprocess, pathlib, shutil, hashlib, pytest

HERE = pathlib.Path(__file__).resolve().parent
CHECKS = [
    "open_file_command_at_canonical_path",
    "search_command_at_canonical_path",
    "safe_path_rejects_traversal_at_canonical_path",
    "scanner_sorts_at_canonical_path",
    "search_result_shape_at_canonical_path",
    "backend_modules_split_not_flattened",
]
_R = {}
MINGW = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages", "BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe", "mingw64", "bin")


def _cargo():
    for c in (os.environ.get("CARGO"), os.path.join(os.environ.get("USERPROFILE", ""), ".cargo", "bin", "cargo.exe"), "cargo"):
        if c and (shutil.which(c) or pathlib.Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("cargo not found")


def _run_rust(ws):
    # Copy the candidate's src-tauri into a stable, identity-keyed working dir and
    # run the reorg harness there. The harness checks both that each canonical
    # module file exists at its path under this copied tree AND that the behavior
    # works, so the existence gate resolves against the candidate's real layout.
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
                       cwd=str(srctauri), env=env, capture_output=True, text=True, timeout=600)
    assert out.exists(), f"rust harness produced no output. stdout={p.stdout[-1500:]} stderr={p.stderr[-1500:]}"
    return json.loads(out.read_text())


def setup_module(m):
    ws = os.environ.get("TOKENBENCH_WORKSPACE") or os.environ.get("WORKSPACE")
    assert ws
    _R.update(_run_rust(ws))


@pytest.mark.parametrize("name", CHECKS)
def test_check(name):
    assert _R.get(name) is True, f"{name}={_R.get(name)!r}"
