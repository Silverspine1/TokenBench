import pytest
from pydantic import ValidationError

from tokenbench.telemetry.schema import ProviderUsage, Telemetry


def _minimal() -> dict:
    return {
        "run_id": "r1",
        "repo_id": "repo",
        "task_id": "task",
        "condition_id": "c",
        "agent_id": "claude_code",
        "trial_index": 1,
        "timing": {
            "agent_wall_time_seconds": 1.0,
            "visible_test_wall_time_seconds": 0.5,
            "hidden_test_wall_time_seconds": 0.5,
            "total_wall_time_seconds": 2.0,
        },
        "prompt": {"prompt_chars": 8, "prompt_bytes": 8, "prompt_estimated_tokens": 2},
        "logs": {
            "agent_stdout_bytes": 10,
            "agent_stderr_bytes": 0,
            "visible_stdout_bytes": 0,
            "visible_stderr_bytes": 0,
            "hidden_stdout_bytes": 0,
            "hidden_stderr_bytes": 0,
            "total_log_bytes": 10,
            "estimated_log_tokens": 3,
        },
        "patch": {
            "changed_files_total": 1,
            "changed_scored_files": 1,
            "changed_ignored_files": 0,
            "changed_forbidden_files": 0,
            "added_files": 0,
            "modified_files": 1,
            "deleted_files": 0,
            "patch_bytes": 40,
            "patch_estimated_tokens": 10,
            "lines_added": 2,
            "lines_deleted": 1,
            "line_churn": 3,
        },
        "commands": {
            "agent_command": ["claude", "--print"],
            "visible_commands_run": 1,
            "hidden_commands_run": 1,
            "test_commands_total": 2,
            "dependency_download_events": 0,
            "detected_install_markers": [],
        },
        "results": {
            "visible_pass_rate": 1.0,
            "hidden_pass_rate": 1.0,
            "quality_score": 100.0,
            "success": True,
            "final_score": 98.0,
        },
        "provider_usage": {"available": False, "source": None, "raw": {}},
        "token_estimates": {
            "estimator": "chars_div_4_v1",
            "prompt_input_tokens": 2,
            "agent_stdout_output_tokens": 3,
            "agent_stderr_output_tokens": 0,
            "agent_total_output_tokens": 3,
            "visible_test_output_tokens": 0,
            "hidden_test_output_tokens": 0,
            "tool_test_output_tokens": 0,
            "patch_tokens": 10,
            "total_observed_tokens": 15,
        },
        "estimates": {
            "estimated_total_observed_tokens": 15,
            "token_estimator": "chars_div_4_v1",
        },
    }


def test_minimal_telemetry_validates():
    t = Telemetry.model_validate(_minimal())
    assert t.estimates.token_estimator == "chars_div_4_v1"
    assert t.provider_usage.available is False


def test_provider_usage_defaults_to_unavailable():
    pu = ProviderUsage()
    assert pu.available is False
    assert pu.source is None
    assert pu.input_tokens is None
    assert pu.total_tokens is None
    assert pu.cost_usd is None
    assert pu.raw == {}


def test_missing_required_block_rejected():
    bad = _minimal()
    del bad["timing"]
    with pytest.raises(ValidationError):
        Telemetry.model_validate(bad)
