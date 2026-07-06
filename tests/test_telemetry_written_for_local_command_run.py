import json
import sys
from pathlib import Path

from tokenbench.cli import execute_run
from tokenbench.manifests.loader import load_manifest
from tokenbench.runners.local_command import LocalCommandRunner
from tokenbench.telemetry.schema import Telemetry

ROOT = Path(__file__).resolve().parents[1]
MARKETLAB = ROOT / "benchmark/manifests/marketlab-ml/marketlab_fee_slippage_001.json"


def test_local_command_run_writes_telemetry(tmp_path):
    manifest = load_manifest(MARKETLAB)
    # A no-op command: makes no edits, writes no prompt.txt.
    runner = LocalCommandRunner(command=f'"{sys.executable}" -c "pass"')

    execute_run(
        manifest, ROOT, runner,
        condition_id="local_baseline", trial_index=0,
        overwrite=True, runs_root=tmp_path,
    )

    run_dir = next(p for p in tmp_path.glob("*/") if (p / "score.json").exists())
    data = json.loads((run_dir / "telemetry.json").read_text(encoding="utf-8"))
    Telemetry.model_validate(data)

    # local-command runner writes no prompt.txt => prompt metrics are zeroed.
    assert (run_dir / "prompt.txt").exists() is False
    assert data["prompt"]["prompt_chars"] == 0
    assert data["prompt"]["prompt_bytes"] == 0
    assert data["prompt"]["prompt_estimated_tokens"] == 0

    # Telemetry still produced and linked.
    assert json.loads((run_dir / "score.json").read_text(encoding="utf-8"))[
        "telemetry_path"
    ] == "telemetry.json"
