import json
import zipfile
from pathlib import Path

from tokenbench.manual.bundles import export_bundle
from tokenbench.manual.service import create_manual_run


def test_bundle_excludes_hidden_and_private(demo_task):
    base = demo_task["base"]
    rec = create_manual_run(base, demo_task["manifest"], condition_id="manual_generic_ide")
    run_dir = Path(rec["run_dir"])

    out_zip = run_dir / "bundle.zip"
    info = export_bundle(base, run_dir, out_zip)
    assert out_zip.exists()
    assert info["bundle_hash"]

    with zipfile.ZipFile(out_zip) as zf:
        names = zf.namelist()
        blob = b"".join(zf.read(n) for n in names)

    # No benchmark-internal artifact present.
    for forbidden in ("task_manifest.json", "score.json", "hidden_tests", "run_state.json"):
        assert not any(forbidden in n for n in names), forbidden

    # The leak token (planted in private fields) is nowhere in the bundle bytes.
    assert demo_task["private_token"].encode() not in blob

    # Hidden command string is not in the public manifest.
    with zipfile.ZipFile(out_zip) as zf:
        pub = json.loads(zf.read("public_manifest.json"))
    assert "hidden_commands" not in pub
    assert "sys.exit" not in json.dumps(pub)

    # Expected contents are present.
    assert any(n.startswith("workspace/") for n in names)
    assert "prompt.txt" in names
    assert "public_manifest.json" in names
    assert "README_INSTRUCTIONS.md" in names
