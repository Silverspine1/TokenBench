"""One-off: rebuild broken snapshots from the scrubbed gold snapshot.

Each broken snapshot == gold snapshot, except the single buggy file (kept as-is)
and a per-task ``tests_visible/`` holding only that task's visible smoke test.
Run from the project root: ``python scripts/_gen_snapshots.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPOS = BASE / "benchmark" / "repos"

SKIP = {"__pycache__", ".pytest_cache", "tests_visible"}

MARKETLAB = {
    "marketlab_fee_slippage_001": ("marketlab/backtest.py", "test_fee_slippage.py"),
    "marketlab_lookahead_feature_001": ("marketlab/features.py", "test_feature.py"),
    "marketlab_split_leakage_001": ("marketlab/split.py", "test_split.py"),
    "marketlab_max_drawdown_001": ("marketlab/backtest.py", "test_metrics.py"),
    "marketlab_label_alignment_001": ("marketlab/labels.py", "test_labels.py"),
}

PULSEBOARD = {
    "pulseboard_contract_001": ("src/contract.js", "contract"),
    "pulseboard_invoice_export_001": ("src/export.js", "export"),
    "pulseboard_pagination_001": ("src/pagination.js", "pagination"),
    "pulseboard_datefilter_001": ("src/datefilter.js", "datefilter"),
    "pulseboard_summary_001": ("src/summary.js", "summary"),
}

# Per-task visible check bodies for pulseboard (mirror gold/tests_visible).
PB_CHECKS = {
    "contract": """  const { normalizeInvoice } = require(path.join(SRC, "contract.js"));
  const out = normalizeInvoice({ id: 7, status: "paid", amount_cents: 1299 });
  assert.strictEqual(out.id, 7);
  assert.strictEqual(out.status, "paid");
  console.log("contract: visible OK");""",
    "datefilter": """  const { invoicesDueOnOrBefore } = require(path.join(SRC, "datefilter.js"));
  const invoices = [
    { id: 1, dueDate: "2026-06-10T12:00:00-05:00" },
    { id: 2, dueDate: "2026-06-20T12:00:00-05:00" },
  ];
  const kept = invoicesDueOnOrBefore(invoices, "2026-06-15");
  assert.deepStrictEqual(kept.map((i) => i.id), [1], "expected only the early invoice");
  console.log("datefilter: visible OK");""",
    "pagination": """  const { paginate } = require(path.join(SRC, "pagination.js"));
  const items = Array.from({ length: 10 }, (_, i) => i + 1);
  const page = paginate(items, 1, 5);
  assert.ok(Array.isArray(page), "expected an array");
  assert.strictEqual(page.length, 5, "page length should equal pageSize");
  console.log("pagination: visible OK");""",
    "export": """  const { exportInvoicesToCsv } = require(path.join(SRC, "export.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const csv = exportInvoicesToCsv(invoices, { status: "paid" });
  const lines = csv.split("\\n");
  assert.strictEqual(lines.length, 2, "expected header + 1 filtered row");
  assert.ok(csv.includes("1,100,paid"), "filtered invoice missing");
  assert.ok(!csv.includes("2,200,open"), "unfiltered invoice present in export");
  console.log("export: visible OK");""",
    "summary": """  const { summarizeByStatus } = require(path.join(SRC, "summary.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const summary = summarizeByStatus(invoices);
  assert.strictEqual(summary.paid.count, 1);
  assert.strictEqual(summary.open.count, 1);
  console.log("summary: visible OK");""",
}

PB_RUNNER_TEMPLATE = '''"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
__BODY__
}

check();
console.log("all visible checks passed");
'''


def iter_gold_files(gold: Path):
    for p in gold.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(gold)
        if any(part in SKIP for part in rel.parts):
            continue
        yield rel


def sync(repo: str, tasks: dict) -> None:
    gold = REPOS / repo / "gold"
    for task, (buggy_rel, _) in tasks.items():
        broken = REPOS / repo / "broken" / task
        # Mirror gold into broken, keeping the buggy file untouched.
        for rel in iter_gold_files(gold):
            if rel.as_posix() == buggy_rel:
                continue
            dst = broken / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(gold / rel, dst)


def write_marketlab_visible() -> None:
    gold = REPOS / "marketlab-ml" / "gold"
    for task, (_, test_file) in MARKETLAB.items():
        tv = REPOS / "marketlab-ml" / "broken" / task / "tests_visible"
        if tv.exists():
            shutil.rmtree(tv)
        tv.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gold / "tests_visible" / test_file, tv / test_file)


def write_pulseboard_visible() -> None:
    for task, (_, check_name) in PULSEBOARD.items():
        tv = REPOS / "pulseboard-saas" / "broken" / task / "tests_visible"
        if tv.exists():
            shutil.rmtree(tv)
        tv.mkdir(parents=True, exist_ok=True)
        runner = PB_RUNNER_TEMPLATE.replace("__BODY__", PB_CHECKS[check_name])
        (tv / "run_visible_tests.js").write_text(runner, encoding="utf-8")


def main() -> None:
    sync("marketlab-ml", MARKETLAB)
    sync("pulseboard-saas", PULSEBOARD)
    write_marketlab_visible()
    write_pulseboard_visible()
    print("snapshots regenerated")


if __name__ == "__main__":
    main()
