"use strict";

// Hidden tests: status summary with partial payments and credits (P3).
// Totals expose gross/paid/outstanding/credited in cents. Outstanding accounts
// for both payments and credits and clamps at zero on overpayment. Status
// labels are preserved, buckets aggregate independently, and invoices are not
// mutated. Per-case scoring via node:test.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { summarizeByStatus } = require(path.join(ws, "src", "invoices", "summary.js"));
const { computeTotals } = require(path.join(ws, "src", "invoices", "totals.js"));

test("partial payment reduces outstanding", () => {
  const s = summarizeByStatus([{ id: 1, status: "open", amount_cents: 1000, payments: [400] }]);
  assert.strictEqual(s.open.gross, 1000);
  assert.strictEqual(s.open.paid, 400);
  assert.strictEqual(s.open.outstanding, 600);
});

test("multiple payments sum before reducing outstanding", () => {
  const t = computeTotals({ amountCents: 1000, payments: [200, 150, 50] });
  assert.strictEqual(t.paid, 400);
  assert.strictEqual(t.outstanding, 600);
});

test("credit memo reduces outstanding", () => {
  const t = computeTotals({ amountCents: 1000, payments: [300], credits: [200] });
  assert.strictEqual(t.credited, 200);
  assert.strictEqual(t.paid, 300);
  assert.strictEqual(t.outstanding, 500);
});

test("payments and credits together reduce outstanding", () => {
  const t = computeTotals({ amountCents: 1000, payments: [400, 100], credits: [100, 50] });
  assert.strictEqual(t.paid, 500);
  assert.strictEqual(t.credited, 150);
  assert.strictEqual(t.outstanding, 350);
});

test("overpayment by payments clamps outstanding at zero", () => {
  const t = computeTotals({ amountCents: 1000, payments: [1200] });
  assert.strictEqual(t.outstanding, 0, "outstanding must not go negative");
});

test("overpayment by credits alone clamps outstanding at zero", () => {
  const t = computeTotals({ amountCents: 1000, credits: [1500] });
  assert.strictEqual(t.credited, 1500);
  assert.strictEqual(t.outstanding, 0, "credits alone must not drive outstanding negative");
});

test("zero / missing payment fields default to gross outstanding", () => {
  const t = computeTotals({ amountCents: 1000 });
  assert.strictEqual(t.paid, 0);
  assert.strictEqual(t.credited, 0);
  assert.strictEqual(t.outstanding, 1000);
});

test("buckets aggregate independently across statuses", () => {
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, payments: [400] },
    { id: 2, status: "open", amount_cents: 500, payments: [500] },
    { id: 3, status: "paid", amount_cents: 800, payments: [800] },
  ]);
  assert.strictEqual(s.open.count, 2);
  assert.strictEqual(s.open.gross, 1500);
  assert.strictEqual(s.open.paid, 900);
  assert.strictEqual(s.open.outstanding, 600);
  assert.strictEqual(s.paid.count, 1);
  assert.strictEqual(s.paid.outstanding, 0);
});

test("outstanding sums per-invoice clamps, not the bucket gross minus paid", () => {
  // One overpaid invoice must NOT subsidise an underpaid one in the bucket.
  // Per-invoice: A outstanding 0 (overpaid), B outstanding 600. Bucket = 600.
  // A naive bucket-level (gross - paid) would give (1000+1000) - (1500+400) = 100.
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, payments: [1500] },
    { id: 2, status: "open", amount_cents: 1000, payments: [400] },
  ]);
  assert.strictEqual(s.open.outstanding, 600);
});

test("status labels preserved and invoices not mutated", () => {
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
