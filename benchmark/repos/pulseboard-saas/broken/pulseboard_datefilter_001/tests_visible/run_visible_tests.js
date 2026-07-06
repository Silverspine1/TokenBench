"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
  const { invoicesDueOnOrBefore } = require(path.join(SRC, "datefilter.js"));
  const invoices = [
    { id: 1, dueDate: "2026-06-10T12:00:00-05:00" },
    { id: 2, dueDate: "2026-06-20T12:00:00-05:00" },
  ];
  const kept = invoicesDueOnOrBefore(invoices, "2026-06-15");
  assert.deepStrictEqual(kept.map((i) => i.id), [1], "expected only the early invoice");
  console.log("datefilter: visible OK");
}

check();
console.log("all visible checks passed");
