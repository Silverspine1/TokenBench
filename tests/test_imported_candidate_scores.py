import zipfile
from pathlib import Path

from tokenbench.manual.bundles import import_candidate
from tokenbench.manual.service import create_manual_run


def _make_candidate_zip(zip_path: Path) -> None:
    """A candidate workspace with the fix applied, zipped under workspace/."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("workspace/demo/app.py", "def add(a, b):\n    return a + b\n")


def test_import_candidate_replaces_workspace_and_scores(demo_task, tmp_path):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])

    zip_path = tmp_path / "candidate.zip"
    _make_candidate_zip(zip_path)

    report = import_candidate(base, run_dir, zip_path)

    assert (run_dir / "score.json").exists()
    assert report["success"] is True
    candidate_app = run_dir / "candidate" / "demo" / "app.py"
    assert "a + b" in candidate_app.read_text(encoding="utf-8")

    import json

    record = json.loads((run_dir / "manual_ide.json").read_text(encoding="utf-8"))
    assert record["candidate_source"] == "bundle_import"
    assert record["candidate_zip_hash"]
