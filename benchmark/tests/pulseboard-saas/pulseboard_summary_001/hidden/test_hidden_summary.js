"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { summarizeByStatus } = require(path.join(ws, "src", "summary.js"));

const invoices = [
  { id: 1, amount: 100, status: "paid" },
  { id: 2, amount: 200, status: "open" },
  { id: 3, amount: 50, status: "paid" },
];
const frozen = JSON.stringify(invoices);

const summary = summarizeByStatus(invoices);

// Counts and totals per status.
assert.strictEqual(summary.paid.count, 2);
assert.strictEqual(summary.paid.total, 150);
assert.strictEqual(summary.open.count, 1);
assert.strictEqual(summary.open.total, 200);

// Input array must not be mutated.
assert.strictEqual(JSON.stringify(invoices), frozen, "input array was mutated");

console.log("hidden OK");
