"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { selectInvoices, exportInvoicesToCsv } = require(path.join(ws, "src", "export.js"));

const invoices = [
  { id: 1, amount: 100, status: "paid" },
  { id: 2, amount: 200, status: "open" },
  { id: 3, amount: 300, status: "paid" },
];

// Filtering selects only matching invoices.
assert.strictEqual(selectInvoices(invoices, { status: "paid" }).length, 2);
assert.strictEqual(selectInvoices(invoices, { status: "open" }).length, 1);

// No filter returns everything.
assert.strictEqual(selectInvoices(invoices, null).length, 3);

// CSV export honors the filter.
const csv = exportInvoicesToCsv(invoices, { status: "open" });
const lines = csv.split("\n");
assert.strictEqual(lines.length, 2, "expected header + 1 open invoice");
assert.ok(csv.includes("2,200,open"));
assert.ok(!csv.includes("paid"), "paid invoices leaked into open-only export");

console.log("hidden OK");
