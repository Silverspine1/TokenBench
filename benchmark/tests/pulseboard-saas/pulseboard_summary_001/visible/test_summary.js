"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { summarizeByStatus } = require(path.join(ws, "src", "summary.js"));

const invoices = [
  { id: 1, amount: 100, status: "paid" },
  { id: 2, amount: 200, status: "open" },
];
const summary = summarizeByStatus(invoices);
assert.strictEqual(summary.paid.count, 1);
assert.strictEqual(summary.open.count, 1);

console.log("visible OK");
