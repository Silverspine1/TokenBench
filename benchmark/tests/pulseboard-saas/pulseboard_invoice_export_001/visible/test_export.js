"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { exportInvoicesToCsv } = require(path.join(ws, "src", "export.js"));

const invoices = [
  { id: 1, amount: 100, status: "paid" },
  { id: 2, amount: 200, status: "open" },
];

const csv = exportInvoicesToCsv(invoices, { status: "paid" });
const lines = csv.split("\n");

assert.strictEqual(lines.length, 2, "expected header + 1 filtered row");
assert.ok(csv.includes("1,100,paid"), "filtered invoice missing");
assert.ok(!csv.includes("2,200,open"), "unfiltered invoice leaked into export");

console.log("visible OK");
