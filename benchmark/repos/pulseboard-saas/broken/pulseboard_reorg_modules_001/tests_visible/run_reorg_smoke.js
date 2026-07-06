"use strict";

// Reorg smoke test. Exercises the public entrypoint only (src/index.js), so it
// runs regardless of how the internals are laid out. Workspace-relative:
//   node tests_visible/run_reorg_smoke.js

const path = require("path");
const assert = require("assert");

const api = require(path.join(__dirname, "..", "src", "index.js"));

const invoices = [
  { id: 1, status: "open", amount_cents: 1000, payments: [400] },
  { id: 2, status: "paid", amount_cents: 500, payments: [500] },
];

const summary = api.summarizeByStatus(invoices);
assert.strictEqual(summary.open.outstanding, 600, "open outstanding");
assert.strictEqual(summary.paid.outstanding, 0, "paid outstanding");

const filtered = api.filterInvoices(invoices, { status: "open" });
assert.strictEqual(filtered.length, 1, "filter by status");

const csv = api.exportFilteredToCsv(invoices, { status: "open" });
assert.strictEqual(csv.split("\n").length, 2, "export header + 1 row");

console.log("reorg smoke OK");
