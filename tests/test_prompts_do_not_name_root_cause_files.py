from pathlib import Path

import pytest

from tokenbench.manifests.loader import load_manifest
from tokenbench.suites.loader import load_suite

ROOT = Path(__file__).resolve().parents[1]
HARD_SUITE = ROOT / "benchmark/suites/v0_5_hard.json"

SUITE = load_suite(HARD_SUITE)
TASK_RELS = list(SUITE.tasks)


@pytest.mark.parametrize("task_rel", TASK_RELS, ids=lambda p: Path(p).stem)
def test_prompt_does_not_name_any_root_cause_file(task_rel):
    manifest = load_manifest(ROOT / task_rel)
    prompt_lc = manifest.prompt.lower().replace("\\", "/")
    for rcf in manifest.root_cause_files:
        rcf_norm = rcf.replace("\\", "/").lower()
        base_name = rcf_norm.rsplit("/", 1)[-1]
        assert rcf_norm not in prompt_lc, (manifest.task_id, rcf)
        assert base_name not in prompt_lc, (manifest.task_id, base_name)
