"""Trial aggregation across runs, grouped by condition.

Trials are grouped internally by (condition_id, repo_id, task_id, runner); the
emitted summary rolls those up to one record per condition_id.
"""

from __future__ import annotations

from pathlib import Path

from .loading import _mean, _median, _nested, load_scores, load_telemetry


def _telemetry_metric(score: dict, telemetry: dict | None, *keys: str) -> float:
    """Pull a numeric telemetry field for a run; 0.0 when telemetry is absent."""
    if not telemetry:
        return 0.0
    cur: object = telemetry
    for k in keys:
        if not isinstance(cur, dict):
            return 0.0
        cur = cur.get(k, 0.0)
    return float(cur) if isinstance(cur, (int, float)) else 0.0


def _provider_value(telemetry: dict | None, key: str) -> float | None:
    """Provider-reported number for a run, or None when unavailable.

    Returns None unless ``provider_usage.available`` is true and the field is
    numeric — never coerces a missing/null provider figure to 0.
    """
    if not telemetry:
        return None
    pu = telemetry.get("provider_usage")
    if not isinstance(pu, dict) or not pu.get("available"):
        return None
    v = pu.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _mean_or_none(values: list[float | None]) -> float | None:
    """Mean over the non-None values; None when none are available."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 4)


def _median_or_none(values: list[float | None]) -> float | None:
    """Median over the non-None values; None when none are available."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(_median(present), 4)


def _sum_or_none(values: list[float | None]) -> float | None:
    """Sum over the non-None values; None when none are available."""
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present), 4)


def aggregate_runs(runs_dir: Path) -> list[dict]:
    """Return one aggregate record per condition_id, sorted by condition_id.

    Telemetry metrics (line churn, estimated tokens, etc.) join in by run_id
    from telemetry.json; runs without a telemetry artifact contribute 0 there.
    """
    scores = load_scores(runs_dir)
    telemetry = load_telemetry(runs_dir)

    groups: dict[str, list[dict]] = {}
    for s in scores:
        cid = s.get("condition_id", "unspecified")
        groups.setdefault(cid, []).append(s)

    out: list[dict] = []
    for cid in sorted(groups):
        items = groups[cid]
        n = len(items)
        tasks = {(x.get("repo_id"), x.get("task_id")) for x in items}
        quality_80 = sum(1 for x in items if float(x.get("quality_score", 0.0)) >= 80.0)
        successes = sum(1 for x in items if bool(x.get("success", False)))

        def _tel(x: dict, *keys: str) -> float:
            return _telemetry_metric(x, telemetry.get(x.get("run_id")), *keys)

        # Agent wall time: prefer telemetry, fall back to the score's timing.
        agent_wall = [
            _tel(x, "timing", "agent_wall_time_seconds")
            or _nested(x, "timing", "agent_wall_time_seconds")
            for x in items
        ]
        log_bytes = [_nested(x, "usage_proxy", "total_log_bytes") for x in items]
        line_churn = [_tel(x, "patch", "line_churn") for x in items]
        scored_files = [_tel(x, "patch", "changed_scored_files") for x in items]
        est_tokens = [
            _tel(x, "estimates", "estimated_total_observed_tokens") for x in items
        ]
        dep_events = [
            _nested(x, "penalties", "dependency_download_events") for x in items
        ]

        # --- token breakdown (estimates) -----------------------------------
        prompt_input = [_tel(x, "token_estimates", "prompt_input_tokens") for x in items]
        agent_output = [
            _tel(x, "token_estimates", "agent_total_output_tokens") for x in items
        ]
        tool_output = [
            _tel(x, "token_estimates", "tool_test_output_tokens") for x in items
        ]
        patch_tokens = [_tel(x, "token_estimates", "patch_tokens") for x in items]
        total_observed = [
            _tel(x, "token_estimates", "total_observed_tokens") for x in items
        ]

        # --- provider-reported usage (null unless really available) --------
        tels = [telemetry.get(x.get("run_id")) for x in items]
        provider_available = sum(
            1 for t in tels if isinstance(t, dict)
            and isinstance(t.get("provider_usage"), dict)
            and t["provider_usage"].get("available")
        )
        prov_input = [_provider_value(t, "input_tokens") for t in tels]
        prov_output = [_provider_value(t, "output_tokens") for t in tels]
        prov_total = [_provider_value(t, "total_tokens") for t in tels]
        prov_cost = [_provider_value(t, "cost_usd") for t in tels]

        out.append(
            {
                "condition_id": cid,
                "tasks_attempted": len(tasks),
                "trials_total": n,
                "success_rate": round(successes / n, 4) if n else 0.0,
                "mean_quality_score": round(_mean([float(x.get("quality_score", 0.0)) for x in items]), 4),
                "mean_efficiency_score": round(_mean([float(x.get("efficiency_score", 0.0)) for x in items]), 4),
                "mean_final_score": round(_mean([float(x.get("final_score", 0.0)) for x in items]), 4),
                "success_rate_quality_80": round(quality_80 / n, 4) if n else 0.0,
                "mean_wall_time_seconds": round(
                    _mean([_nested(x, "timing", "total_wall_time_seconds") for x in items]), 4
                ),
                # --- telemetry metrics (calibration evidence) ----------------
                "mean_agent_wall_time_seconds": round(_mean(agent_wall), 4),
                "median_agent_wall_time_seconds": round(_median(agent_wall), 4),
                "mean_total_log_bytes": round(_mean(log_bytes), 4),
                "median_total_log_bytes": round(_median(log_bytes), 4),
                "mean_line_churn": round(_mean(line_churn), 4),
                "median_line_churn": round(_median(line_churn), 4),
                "mean_changed_scored_files": round(_mean(scored_files), 4),
                "median_changed_scored_files": round(_median(scored_files), 4),
                "mean_estimated_total_observed_tokens": round(_mean(est_tokens), 4),
                "median_estimated_total_observed_tokens": round(_median(est_tokens), 4),
                "mean_dependency_download_events": round(_mean(dep_events), 4),
                # --- token breakdown (estimates) --------------------------
                "mean_prompt_input_tokens": round(_mean(prompt_input), 4),
                "median_prompt_input_tokens": round(_median(prompt_input), 4),
                "mean_agent_output_tokens": round(_mean(agent_output), 4),
                "median_agent_output_tokens": round(_median(agent_output), 4),
                "mean_tool_test_output_tokens": round(_mean(tool_output), 4),
                "median_tool_test_output_tokens": round(_median(tool_output), 4),
                "mean_patch_tokens": round(_mean(patch_tokens), 4),
                "median_patch_tokens": round(_median(patch_tokens), 4),
                "mean_total_observed_tokens": round(_mean(total_observed), 4),
                "median_total_observed_tokens": round(_median(total_observed), 4),
                # --- provider-reported usage (null unless available) ------
                "provider_usage_available_rate": round(provider_available / n, 4) if n else 0.0,
                "mean_provider_input_tokens": _mean_or_none(prov_input),
                "mean_provider_output_tokens": _mean_or_none(prov_output),
                "mean_provider_total_tokens": _mean_or_none(prov_total),
                "median_provider_total_tokens": _median_or_none(prov_total),
                "total_provider_cost_usd": _sum_or_none(prov_cost),
                "mean_provider_cost_usd": _mean_or_none(prov_cost),
                "median_provider_cost_usd": _median_or_none(prov_cost),
            }
        )
    return out
