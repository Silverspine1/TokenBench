"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
  const { exportInvoicesToCsv } = require(path.join(SRC, "export.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const csv = exportInvoicesToCsv(invoices, { status: "paid" });
  const lines = csv.split("\n");
  assert.strictEqual(lines.length, 2, "expected header + 1 filtered row");
  assert.ok(csv.includes("1,100,paid"), "filtered invoice missing");
  assert.ok(!csv.includes("2,200,open"), "unfiltered invoice present in export");
  console.log("export: visible OK");
}

check();
console.log("all visible checks passed");
