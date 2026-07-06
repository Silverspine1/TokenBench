"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { invoicesDueOnOrBefore } = require(path.join(ws, "src", "datefilter.js"));

// Clearly-before is kept, clearly-after is dropped (no boundary day involved).
const invoices = [
  { id: 1, dueDate: "2026-06-10T12:00:00-05:00" },
  { id: 2, dueDate: "2026-06-20T12:00:00-05:00" },
];
const kept = invoicesDueOnOrBefore(invoices, "2026-06-15");
assert.deepStrictEqual(kept.map((i) => i.id), [1], "expected only the early invoice");

console.log("visible OK");
