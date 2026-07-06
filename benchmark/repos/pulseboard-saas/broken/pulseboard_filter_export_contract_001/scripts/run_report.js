"use strict";

// Build and print a filtered invoice report. Convenience wrapper for manual use.

const path = require("path");
const { buildReport } = require(path.join(__dirname, "..", "src", "api", "reportsApi.js"));

const invoices = [
  { id: 1, status: "open", amount_cents: 10000, customer_name: "Acme" },
  { id: 2, status: "paid", amount_cents: 25000, customer_name: "Globex" },
];

const report = buildReport(invoices, { status: "open" });
console.log(JSON.stringify({ count: report.count, summary: report.summary }, null, 2));
