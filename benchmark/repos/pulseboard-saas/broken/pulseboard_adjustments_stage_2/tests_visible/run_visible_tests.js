"use strict";

// Visible smoke tests. Runs from the project root: `node tests_visible/run_visible_tests.js`.
// Modules are resolved relative to this file so the command is workspace-relative.

const path = require("path");
const assert = require("assert");

const SRC = path.join(__dirname, "..", "src");

function checkContract() {
  const { normalizeInvoice } = require(path.join(SRC, "contract.js"));
  const out = normalizeInvoice({ id: 7, status: "paid", amount_cents: 1299 });
  assert.strictEqual(out.id, 7);
  assert.strictEqual(out.status, "paid");
  console.log("contract: visible OK");
}

function checkDatefilter() {
  const { invoicesDueOnOrBefore } = require(path.join(SRC, "datefilter.js"));
  const invoices = [
    { id: 1, dueDate: "2026-06-10T12:00:00-05:00" },
    { id: 2, dueDate: "2026-06-20T12:00:00-05:00" },
  ];
  const kept = invoicesDueOnOrBefore(invoices, "2026-06-15");
  assert.deepStrictEqual(kept.map((i) => i.id), [1], "expected only the early invoice");
  console.log("datefilter: visible OK");
}

function checkPagination() {
  const { paginate } = require(path.join(SRC, "pagination.js"));
  const items = Array.from({ length: 10 }, (_, i) => i + 1);
  const page = paginate(items, 1, 5);
  assert.ok(Array.isArray(page), "expected an array");
  assert.strictEqual(page.length, 5, "page length should equal pageSize");
  console.log("pagination: visible OK");
}

function checkExport() {
  const { exportInvoicesToCsv } = require(path.join(SRC, "export.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const csv = exportInvoicesToCsv(invoices, { status: "paid" });
  const lines = csv.split("\n");
  assert.strictEqual(lines.length, 2, "expected header + 1 filtered row");
  assert.ok(csv.includes("1,100,paid"), "filtered invoice missing");
  assert.ok(!csv.includes("2,200,open"), "unfiltered invoice present in export");
  console.log("export: visible OK");
}

function checkSummary() {
  const { summarizeByStatus } = require(path.join(SRC, "summary.js"));
  const invoices = [
    { id: 1, amount: 100, status: "paid" },
    { id: 2, amount: 200, status: "open" },
  ];
  const summary = summarizeByStatus(invoices);
  assert.strictEqual(summary.paid.count, 1);
  assert.strictEqual(summary.open.count, 1);
  console.log("summary: visible OK");
}

function checkSchemaCompat() {
  const { normalizeInvoice } = require(path.join(SRC, "invoices", "schema.js"));
  const flat = normalizeInvoice({ id: 1, status: "open", amount_cents: 1299 });
  const nested = normalizeInvoice({ id: 2, status: "open", amount: { cents: 1299 } });
  assert.strictEqual(flat.amountCents, 1299);
  assert.strictEqual(nested.amountCents, 1299);
  console.log("schema: visible OK");
}

function checkFilterExport() {
  const { filterInvoices } = require(path.join(SRC, "invoices", "filters.js"));
  const { exportFilteredToCsv } = require(path.join(SRC, "invoices", "export.js"));
  const invoices = [
    { id: 1, status: "open", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "paid", amount_cents: 200, customer_name: "B" },
  ];
  const filtered = filterInvoices(invoices, { status: "open" });
  assert.strictEqual(filtered.length, 1);
  const csv = exportFilteredToCsv(invoices, { status: "open" });
  assert.strictEqual(csv.split("\n").length, 2);
  console.log("filter/export: visible OK");
}

function checkSummaryTotals() {
  const { summarizeByStatus } = require(path.join(SRC, "invoices", "summary.js"));
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, payments: [400] },
  ]);
  assert.strictEqual(s.open.outstanding, 600);
  console.log("summary-totals: visible OK");
}

function checkCache() {
  const { InvoiceState } = require(path.join(SRC, "state", "invoiceState.js"));
  const state = new InvoiceState([{ id: 1, status: "open", amount_cents: 100 }]);
  state.getFilteredReport({ status: "open" });
  state.getFilteredReport({ status: "open" });
  assert.strictEqual(state.computeCount, 1, "second identical query should hit cache");
  console.log("cache: visible OK");
}

checkContract();
checkDatefilter();
checkPagination();
checkExport();
checkSummary();
checkSchemaCompat();
checkFilterExport();
checkSummaryTotals();
checkCache();
console.log("all visible checks passed");
