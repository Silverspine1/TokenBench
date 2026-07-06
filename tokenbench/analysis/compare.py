"""Paired comparison of two conditions on matching (repo, task, trial) cells."""

from __future__ import annotations

from pathlib import Path

from .loading import _nested, load_scores, load_telemetry


def _key(s: dict) -> tuple:
    return (s.get("repo_id"), s.get("task_id"), int(s.get("trial_index", 0)))


def _tel(telemetry: dict, run_id, *keys: str) -> float:
    """Numeric telemetry field for a run; 0.0 when telemetry is absent."""
    cur: object = telemetry.get(run_id)
    for k in keys:
        if not isinstance(cur, dict):
            return 0.0
        cur = cur.get(k, 0.0)
    return float(cur) if isinstance(cur, (int, float)) else 0.0


def _runtime(s: dict, telemetry: dict) -> float:
    return _tel(telemetry, s.get("run_id"), "timing", "agent_wall_time_seconds") or _nested(
        s, "timing", "agent_wall_time_seconds"
    )


def _log_bytes(s: dict) -> float:
    return _nested(s, "usage_proxy", "total_log_bytes")


def _est_tokens(s: dict, telemetry: dict) -> float:
    return _tel(telemetry, s.get("run_id"), "estimates", "estimated_total_observed_tokens")


def _line_churn(s: dict, telemetry: dict) -> float:
    return _tel(telemetry, s.get("run_id"), "patch", "line_churn")


def _token(s: dict, telemetry: dict, field: str) -> float:
    return _tel(telemetry, s.get("run_id"), "token_estimates", field)


def compare_conditions(runs_dir: Path, condition_a: str, condition_b: str) -> dict:
    """Compare condition_b against condition_a on matching cells.

    Deltas are condition_b minus condition_a. Only cells present in both
    conditions are paired. Pairs are processed in sorted-key order so output is
    deterministic; with duplicate cells the highest run_id wins (scores arrive
    run_id-sorted).
    """
    scores = load_scores(runs_dir)
    telemetry = load_telemetry(runs_dir)

    a: dict[tuple, dict] = {}
    b: dict[tuple, dict] = {}
    for s in scores:
        cid = s.get("condition_id")
        if cid == condition_a:
            a[_key(s)] = s
        elif cid == condition_b:
            b[_key(s)] = s

    pairs = sorted(set(a) & set(b))

    final_deltas: list[float] = []
    quality_deltas: list[float] = []
    efficiency_deltas: list[float] = []
    success_deltas: list[float] = []
    runtime_deltas: list[float] = []
    log_bytes_deltas: list[float] = []
    line_churn_deltas: list[float] = []
    est_tokens_deltas: list[float] = []
    # Per-condition means of the raw quantities, for percent-savings reporting.
    runtime_a: list[float] = []
    runtime_b: list[float] = []
    log_bytes_a: list[float] = []
    log_bytes_b: list[float] = []
    est_tokens_a: list[float] = []
    est_tokens_b: list[float] = []
    # Token breakdown deltas + per-condition raw means for percent savings.
    TOKEN_FIELDS = (
        ("prompt_input", "prompt_input_tokens"),
        ("agent_output", "agent_total_output_tokens"),
        ("tool_test_output", "tool_test_output_tokens"),
        ("patch", "patch_tokens"),
        ("total_observed", "total_observed_tokens"),
    )
    tok_deltas: dict[str, list[float]] = {name: [] for name, _ in TOKEN_FIELDS}
    tok_a: dict[str, list[float]] = {name: [] for name, _ in TOKEN_FIELDS}
    tok_b: dict[str, list[float]] = {name: [] for name, _ in TOKEN_FIELDS}
    success_a = success_b = 0
    wins_a = wins_b = ties = 0

    for k in pairs:
        sa, sb = a[k], b[k]
        fa, fb = float(sa.get("final_score", 0.0)), float(sb.get("final_score", 0.0))
        final_deltas.append(fb - fa)
        quality_deltas.append(float(sb.get("quality_score", 0.0)) - float(sa.get("quality_score", 0.0)))
        efficiency_deltas.append(
            float(sb.get("efficiency_score", 0.0)) - float(sa.get("efficiency_score", 0.0))
        )

        ra, rb = _runtime(sa, telemetry), _runtime(sb, telemetry)
        la, lb = _log_bytes(sa), _log_bytes(sb)
        ta, tb = _est_tokens(sa, telemetry), _est_tokens(sb, telemetry)
        runtime_deltas.append(rb - ra)
        log_bytes_deltas.append(lb - la)
        line_churn_deltas.append(_line_churn(sb, telemetry) - _line_churn(sa, telemetry))
        est_tokens_deltas.append(tb - ta)
        runtime_a.append(ra)
        runtime_b.append(rb)
        log_bytes_a.append(la)
        log_bytes_b.append(lb)
        est_tokens_a.append(ta)
        est_tokens_b.append(tb)

        for name, field in TOKEN_FIELDS:
            va = _token(sa, telemetry, field)
            vb = _token(sb, telemetry, field)
            tok_deltas[name].append(vb - va)
            tok_a[name].append(va)
            tok_b[name].append(vb)

        a_ok = 1.0 if sa.get("success") else 0.0
        b_ok = 1.0 if sb.get("success") else 0.0
        success_a += int(a_ok)
        success_b += int(b_ok)
        success_deltas.append(b_ok - a_ok)
        if fb > fa:
            wins_b += 1
        elif fa > fb:
            wins_a += 1
        else:
            ties += 1

    n = len(pairs)

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / n, 4) if n else 0.0

    def savings_percent(base: list[float], comp: list[float]) -> float | None:
        """Percent reduction of B relative to A's mean. None when baseline is 0."""
        if not n:
            return None
        base_mean = sum(base) / n
        if base_mean == 0:
            return None
        comp_mean = sum(comp) / n
        return round((base_mean - comp_mean) / base_mean * 100.0, 4)

    return {
        "condition_a": condition_a,
        "condition_b": condition_b,
        "paired_tasks": n,
        "mean_final_delta": mean(final_deltas),
        "mean_quality_delta": mean(quality_deltas),
        "mean_efficiency_delta": mean(efficiency_deltas),
        "mean_success_delta": mean(success_deltas),
        # --- telemetry deltas (B minus A; descriptive, not significant) ------
        "mean_runtime_delta": mean(runtime_deltas),
        "mean_log_bytes_delta": mean(log_bytes_deltas),
        "mean_line_churn_delta": mean(line_churn_deltas),
        "mean_estimated_tokens_delta": mean(est_tokens_deltas),
        # --- token breakdown deltas (B minus A) -------------------------------
        "mean_prompt_input_token_delta": mean(tok_deltas["prompt_input"]),
        "mean_agent_output_token_delta": mean(tok_deltas["agent_output"]),
        "mean_tool_test_output_token_delta": mean(tok_deltas["tool_test_output"]),
        "mean_patch_token_delta": mean(tok_deltas["patch"]),
        "mean_total_observed_token_delta": mean(tok_deltas["total_observed"]),
        # --- percent savings of B vs A (None when A's baseline is 0) ----------
        "estimated_token_savings_percent": savings_percent(est_tokens_a, est_tokens_b),
        "runtime_savings_percent": savings_percent(runtime_a, runtime_b),
        "log_byte_savings_percent": savings_percent(log_bytes_a, log_bytes_b),
        "prompt_input_token_savings_percent": savings_percent(
            tok_a["prompt_input"], tok_b["prompt_input"]
        ),
        "agent_output_token_savings_percent": savings_percent(
            tok_a["agent_output"], tok_b["agent_output"]
        ),
        "tool_test_output_token_savings_percent": savings_percent(
            tok_a["tool_test_output"], tok_b["tool_test_output"]
        ),
        "total_observed_token_savings_percent": savings_percent(
            tok_a["total_observed"], tok_b["total_observed"]
        ),
        "success_rate_a": round(success_a / n, 4) if n else 0.0,
        "success_rate_b": round(success_b / n, 4) if n else 0.0,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "ties": ties,
        # Structure reserved for paired significance testing (not yet computed).
        "final_delta_pvalue": None,
    }
