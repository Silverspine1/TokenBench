"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
  const { normalizeInvoice } = require(path.join(SRC, "contract.js"));
  const out = normalizeInvoice({ id: 7, status: "paid", amount_cents: 1299 });
  assert.strictEqual(out.id, 7);
  assert.strictEqual(out.status, "paid");
  console.log("contract: visible OK");
}

check();
console.log("all visible checks passed");
