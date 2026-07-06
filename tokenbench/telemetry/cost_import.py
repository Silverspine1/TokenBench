"""Manual provider-cost import.

When a CLI does not expose machine-readable cost but a provider dashboard does,
costs can be attached to a run after the fact. Imported figures are marked
``source = "manual"`` and written into ``telemetry.json``'s ``provider_usage``.
These are provider-reported numbers, never estimates — nothing here reads or
derives from the token estimates.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

# Token fields a row/CLI may supply, in provider_usage order.
_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
)


def apply_cost(provider_usage: dict | None, fields: dict) -> dict:
    """Return a provider_usage dict updated with manually supplied figures.

    ``fields`` may carry ``cost_usd``, any of the token fields, and an explicit
    ``total_tokens``. Provided values overwrite; omitted values are left as-is.
    ``total_tokens`` defaults to the sum of the present token fields when not
    given explicitly. The record is marked available with ``source = "manual"``.
    """
    pu = dict(provider_usage) if isinstance(provider_usage, dict) else {}
    pu["available"] = True
    pu["source"] = "manual"

    if "cost_usd" in fields and fields["cost_usd"] is not None:
        pu["cost_usd"] = float(fields["cost_usd"])

    for key in _TOKEN_FIELDS:
        if key in fields and fields[key] is not None:
            pu[key] = int(fields[key])

    if fields.get("total_tokens") is not None:
        pu["total_tokens"] = int(fields["total_tokens"])
    else:
        parts = [pu.get(k) for k in _TOKEN_FIELDS]
        present = [int(p) for p in parts if isinstance(p, (int, float))]
        if present:
            pu["total_tokens"] = sum(present)

    # Ensure every schema field exists (null when never supplied).
    for key in (*_TOKEN_FIELDS, "total_tokens", "cost_usd"):
        pu.setdefault(key, None)
    pu.setdefault("raw", {})
    return pu


def attach_cost_to_run(run_dir: Path, fields: dict) -> dict:
    """Update one run's ``telemetry.json`` provider_usage with manual figures.

    Returns the updated telemetry dict. Raises ``FileNotFoundError`` when the
    run has no telemetry artifact.
    """
    run_dir = Path(run_dir)
    tel_path = run_dir / "telemetry.json"
    if not tel_path.exists():
        raise FileNotFoundError(f"no telemetry.json in {run_dir}")
    telemetry = json.loads(tel_path.read_text(encoding="utf-8"))
    telemetry["provider_usage"] = apply_cost(telemetry.get("provider_usage"), fields)
    tel_path.write_text(json.dumps(telemetry, indent=2), encoding="utf-8")
    return telemetry


def _row_fields(row: dict) -> dict:
    """Coerce a CSV row's numeric columns, dropping empty cells."""
    out: dict = {}
    for key in ("cost_usd", *_TOKEN_FIELDS, "total_tokens"):
        raw = row.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        out[key] = float(raw) if key == "cost_usd" else int(float(raw))
    return out


def attach_cost_csv(csv_path: Path, runs_dir: Path) -> list[dict]:
    """Attach costs to many runs from a CSV keyed by ``run_id``.

    CSV columns: run_id, cost_usd, input_tokens, output_tokens,
    cache_read_tokens, cache_write_tokens, reasoning_tokens, total_tokens.
    Returns one result record per row with its status; a missing run is recorded
    as an error and does not stop the rest.
    """
    csv_path = Path(csv_path)
    runs_dir = Path(runs_dir)
    results: list[dict] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            run_id = (row.get("run_id") or "").strip()
            if not run_id:
                results.append({"run_id": run_id, "status": "error", "error": "missing run_id"})
                continue
            run_dir = runs_dir / run_id
            try:
                attach_cost_to_run(run_dir, _row_fields(row))
                results.append({"run_id": run_id, "status": "ok"})
            except FileNotFoundError as e:
                results.append({"run_id": run_id, "status": "error", "error": str(e)})
    return results
