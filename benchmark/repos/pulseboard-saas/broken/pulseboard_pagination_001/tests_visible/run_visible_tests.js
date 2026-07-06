"use strict";

// Visible smoke test. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function check() {
  const { paginate } = require(path.join(SRC, "pagination.js"));
  const items = Array.from({ length: 10 }, (_, i) => i + 1);
  const page = paginate(items, 1, 5);
  assert.ok(Array.isArray(page), "expected an array");
  assert.strictEqual(page.length, 5, "page length should equal pageSize");
  console.log("pagination: visible OK");
}

check();
console.log("all visible checks passed");
