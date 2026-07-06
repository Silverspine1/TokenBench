"""Baseline calibration report.

Groups a single condition's runs by task and reports per-task medians of the
raw telemetry facts. This is descriptive calibration evidence used to decide a
real efficiency formula later — it makes no efficiency claim itself.
"""

from __future__ import annotations

from pathlib import Path

from ..analysis.loading import _median, _nested, load_scores, load_telemetry


def _tel(telemetry: dict, run_id, *keys: str) -> float:
    cur: object = telemetry.get(run_id)
    for k in keys:
        if not isinstance(cur, dict):
            return 0.0
        cur = cur.get(k, 0.0)
    return float(cur) if isinstance(cur, (int, float)) else 0.0


def _provider_value(telemetry: dict, run_id, key: str) -> float | None:
    """Provider-reported number, or None unless ``available`` and numeric."""
    pu = telemetry.get(run_id)
    pu = pu.get("provider_usage") if isinstance(pu, dict) else None
    if not isinstance(pu, dict) or not pu.get("available"):
        return None
    v = pu.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _median_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(_median(present), 4) if present else None


def _mean_or_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(sum(present) / len(present), 4) if present else None


def calibration_report(runs_dir: Path, condition_id: str) -> dict:
    """Per-task median telemetry for one condition, sorted by (repo, task)."""
    scores = load_scores(runs_dir)
    telemetry = load_telemetry(runs_dir)

    groups: dict[tuple, list[dict]] = {}
    for s in scores:
        if s.get("condition_id") != condition_id:
            continue
        key = (s.get("repo_id"), s.get("task_id"))
        groups.setdefault(key, []).append(s)

    tasks: list[dict] = []
    for (repo_id, task_id) in sorted(groups, key=lambda k: (k[0] or "", k[1] or "")):
        items = groups[(repo_id, task_id)]
        n = len(items)
        successes = sum(1 for x in items if bool(x.get("success", False)))

        def _rt(x: dict) -> float:
            return _tel(telemetry, x.get("run_id"), "timing", "agent_wall_time_seconds") or _nested(
                x, "timing", "agent_wall_time_seconds"
            )

        def _tok(field: str) -> list[float]:
            return [
                _tel(telemetry, x.get("run_id"), "token_estimates", field) for x in items
            ]

        provider_available = sum(
            1 for x in items
            if isinstance(telemetry.get(x.get("run_id")), dict)
            and isinstance(telemetry[x.get("run_id")].get("provider_usage"), dict)
            and telemetry[x.get("run_id")]["provider_usage"].get("available")
        )
        prov_total = [_provider_value(telemetry, x.get("run_id"), "total_tokens") for x in items]
        prov_cost = [_provider_value(telemetry, x.get("run_id"), "cost_usd") for x in items]
        available_rate = round(provider_available / n, 4) if n else 0.0
        # Make the unavailable case explicit so a reader never mistakes a null
        # provider cost for "free" or silently falls back to estimated tokens.
        cost_status = (
            "provider cost unavailable" if available_rate == 0.0 else "provider cost available"
        )

        tasks.append(
            {
                "repo_id": repo_id,
                "task_id": task_id,
                "trials": n,
                "success_rate": round(successes / n, 4) if n else 0.0,
                "median_quality_score": round(
                    _median([float(x.get("quality_score", 0.0)) for x in items]), 4
                ),
                "median_agent_wall_time_seconds": round(_median([_rt(x) for x in items]), 4),
                "median_total_log_bytes": round(
                    _median([_nested(x, "usage_proxy", "total_log_bytes") for x in items]), 4
                ),
                "median_estimated_total_observed_tokens": round(
                    _median(
                        [
                            _tel(telemetry, x.get("run_id"), "estimates",
                                 "estimated_total_observed_tokens")
                            for x in items
                        ]
                    ),
                    4,
                ),
                "median_changed_scored_files": round(
                    _median(
                        [_tel(telemetry, x.get("run_id"), "patch", "changed_scored_files")
                         for x in items]
                    ),
                    4,
                ),
                "median_line_churn": round(
                    _median(
                        [_tel(telemetry, x.get("run_id"), "patch", "line_churn") for x in items]
                    ),
                    4,
                ),
                # --- token breakdown medians (estimates) ------------------
                "median_prompt_input_tokens": round(_median(_tok("prompt_input_tokens")), 4),
                "median_agent_output_tokens": round(
                    _median(_tok("agent_total_output_tokens")), 4
                ),
                "median_tool_test_output_tokens": round(
                    _median(_tok("tool_test_output_tokens")), 4
                ),
                "median_patch_tokens": round(_median(_tok("patch_tokens")), 4),
                "median_total_observed_tokens": round(
                    _median(_tok("total_observed_tokens")), 4
                ),
                # --- provider-reported usage (null unless available) ------
                "provider_usage_available_rate": available_rate,
                "provider_cost_status": cost_status,
                "median_provider_total_tokens": _median_or_none(prov_total),
                "median_provider_cost_usd": _median_or_none(prov_cost),
                "mean_provider_cost_usd": _mean_or_none(prov_cost),
            }
        )

    return {"condition_id": condition_id, "tasks": tasks}
