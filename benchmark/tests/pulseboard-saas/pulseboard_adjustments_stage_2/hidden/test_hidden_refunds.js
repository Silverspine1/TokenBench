"use strict";

// Hidden tests for Stage 2: refunds folded into the same reporting flow as the
// Stage 1 adjustments. A refund is money returned to the customer; it lowers the
// net amount the business kept, so it raises the outstanding balance again. The
// Stage 1 adjustment behaviour must still hold.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { computeTotals } = require(path.join(ws, "src", "invoices", "totals.js"));
const { summarizeByStatus } = require(path.join(ws, "src", "invoices", "summary.js"));

test("a refund reduces net paid and raises outstanding", () => {
  const t = computeTotals({ amountCents: 1000, payments: [1000], refunds: [300] });
  assert.strictEqual(t.refunds, 300);
  assert.strictEqual(t.netPaid, 700);
  assert.strictEqual(t.outstanding, 300);
});

test("refunds compose with adjustments from Stage 1", () => {
  const t = computeTotals({ amountCents: 1000, payments: [800], adjustments: [200], refunds: [100] });
  // 1000 + 200 - (800 - 100) - 0 = 500
  assert.strictEqual(t.adjustments, 200);
  assert.strictEqual(t.refunds, 100);
  assert.strictEqual(t.outstanding, 500);
});

test("a full refund of a fully paid invoice restores the whole balance", () => {
  const t = computeTotals({ amountCents: 1000, payments: [1000], refunds: [1000] });
  assert.strictEqual(t.netPaid, 0);
  assert.strictEqual(t.outstanding, 1000);
});

test("missing refunds default to zero and preserve Stage 1 behaviour", () => {
  const t = computeTotals({ amountCents: 1000, payments: [400], adjustments: [100] });
  assert.strictEqual(t.refunds, 0);
  assert.strictEqual(t.outstanding, 700);
});

test("summary reports refunds per status and reflects them in outstanding", () => {
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, payments: [1000], refunds: [200] },
    { id: 2, status: "open", amount_cents: 500, payments: [500] },
  ]);
  assert.strictEqual(s.open.refunds, 200);
  assert.strictEqual(s.open.outstanding, 200); // inv1: 200, inv2: 0
});

test("multiple refunds on one invoice sum before reducing net paid", () => {
  const t = computeTotals({ amountCents: 1000, payments: [1000], refunds: [100, 150, 50] });
  assert.strictEqual(t.refunds, 300);
  assert.strictEqual(t.outstanding, 300);
});

test("summary keeps adjustments correct alongside refunds", () => {
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, adjustments: [100], payments: [600], refunds: [50] },
  ]);
  assert.strictEqual(s.open.adjustments, 100);
  assert.strictEqual(s.open.refunds, 50);
  assert.strictEqual(s.open.outstanding, 550); // 1000 + 100 - (600 - 50)
});
