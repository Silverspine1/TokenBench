"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
  const { summarizeByStatus } = require(path.join(SRC, "summary.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const summary = summarizeByStatus(invoices);
  assert.strictEqual(summary.paid.count, 1);
  assert.strictEqual(summary.open.count, 1);
  console.log("summary: visible OK");
}

check();
console.log("all visible checks passed");
