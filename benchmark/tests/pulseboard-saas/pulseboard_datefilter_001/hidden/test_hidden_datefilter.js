"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { invoicesDueOnOrBefore } = require(path.join(ws, "src", "datefilter.js"));

// A is due late in the evening of the local end date; in UTC it rolls to the
// next day. It must still be included when the end date is its local due date.
const invoices = [
  { id: 1, dueDate: "2026-06-15T23:30:00-05:00" }, // local 06-15 (UTC 06-16)
  { id: 2, dueDate: "2026-06-15T09:00:00-05:00" }, // local 06-15
  { id: 3, dueDate: "2026-06-16T09:00:00-05:00" }, // local 06-16
];
const kept = invoicesDueOnOrBefore(invoices, "2026-06-15");
const ids = kept.map((i) => i.id).sort();
assert.deepStrictEqual(ids, [1, 2], "late-evening local due date wrongly excluded");

console.log("hidden OK");
