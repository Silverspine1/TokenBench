"use strict";

// Hidden behaviour tests for the invoice/reporting reorganization. Each test
// loads the module it needs at its canonical path inside the test body, so a
// module that is missing or misplaced fails only its own cases (graceful
// partial credit) rather than aborting the whole file. Per-case scoring via
// node:test (TAP).

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const load = (...parts) => require(path.join(ws, "src", ...parts));

test("money: sumCents adds integer cents", () => {
  const { sumCents } = load("shared", "money.js");
  assert.strictEqual(sumCents([200, 150, 50]), 400);
  assert.strictEqual(sumCents([]), 0);
});

test("money: clampNonNegative floors at zero", () => {
  const { clampNonNegative } = load("shared", "money.js");
  assert.strictEqual(clampNonNegative(-5), 0);
  assert.strictEqual(clampNonNegative(40), 40);
});

test("totals: outstanding nets payments and credits", () => {
  const { computeTotals } = load("invoices", "totals.js");
  const t = computeTotals({ amountCents: 1000, payments: [400, 100], credits: [100, 50] });
  assert.strictEqual(t.paid, 500);
  assert.strictEqual(t.credited, 150);
  assert.strictEqual(t.outstanding, 350);
});

test("totals: overpayment clamps outstanding at zero", () => {
  const { computeTotals } = load("invoices", "totals.js");
  assert.strictEqual(computeTotals({ amountCents: 1000, payments: [1200] }).outstanding, 0);
});

test("totals: missing payment fields default to gross outstanding", () => {
  const { computeTotals } = load("invoices", "totals.js");
  const t = computeTotals({ amountCents: 1000 });
  assert.strictEqual(t.paid, 0);
  assert.strictEqual(t.credited, 0);
  assert.strictEqual(t.outstanding, 1000);
});

test("summary: buckets aggregate independently and clamp per invoice", () => {
  const { summarizeByStatus } = load("invoices", "summary.js");
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, payments: [1500] },
    { id: 2, status: "open", amount_cents: 1000, payments: [400] },
  ]);
  assert.strictEqual(s.open.count, 2);
  assert.strictEqual(s.open.outstanding, 600);
});

test("summary: preserves status labels and does not mutate input", () => {
  const { summarizeByStatus } = load("invoices", "summary.js");
  const invoices = [
    { id: 1, status: "overdue", amount_cents: 500, payments: [100] },
    { id: 2, status: "open", amount_cents: 700 },
  ];
  const snapshot = JSON.parse(JSON.stringify(invoices));
  const s = summarizeByStatus(invoices);
  assert.deepStrictEqual(Object.keys(s).sort(), ["open", "overdue"]);
  assert.strictEqual(s.overdue.outstanding, 400);
  assert.deepStrictEqual(invoices, snapshot);
});

test("filters: by status returns a fresh normalized list", () => {
  const { filterInvoices } = load("invoices", "filters.js");
  const invoices = [
    { id: 1, status: "open", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "paid", amount_cents: 200, customer_name: "B" },
  ];
  const rows = filterInvoices(invoices, { status: "open" });
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].amountCents, 100);
});

test("filters: due-on-or-before uses the business offset inclusively", () => {
  const { filterInvoices } = load("invoices", "filters.js");
  const invoices = [
    { id: 1, dueDate: "2026-06-10T12:00:00-05:00" },
    { id: 2, dueDate: "2026-06-20T12:00:00-05:00" },
  ];
  const kept = filterInvoices(invoices, { dueOnOrBefore: "2026-06-15" });
  assert.deepStrictEqual(kept.map((i) => i.id), [1]);
});

test("export: emits the filtered set as CSV with the header row", () => {
  const { exportFilteredToCsv } = load("invoices", "export.js");
  const invoices = [
    { id: 1, status: "open", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "paid", amount_cents: 200, customer_name: "B" },
  ];
  const csv = exportFilteredToCsv(invoices, { status: "open" });
  const lines = csv.split("\n");
  assert.strictEqual(lines.length, 2);
  assert.strictEqual(lines[0], "id,status,amountCents,customerName");
  assert.ok(lines[1].startsWith("1,open,100,A"));
});
