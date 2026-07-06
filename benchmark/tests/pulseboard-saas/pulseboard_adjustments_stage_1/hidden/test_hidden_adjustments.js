"use strict";

// Hidden tests for Stage 1: manual invoice adjustments folded into totals and
// the by-status summary. Adjustments are signed cents (+ surcharge, - discount).
// Existing behaviour (no adjustments) must be unchanged.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { computeTotals } = require(path.join(ws, "src", "invoices", "totals.js"));
const { summarizeByStatus } = require(path.join(ws, "src", "invoices", "summary.js"));

test("positive adjustment (surcharge) increases outstanding", () => {
  const t = computeTotals({ amountCents: 1000, adjustments: [200] });
  assert.strictEqual(t.adjustments, 200);
  assert.strictEqual(t.outstanding, 1200);
});

test("negative adjustment (discount) decreases outstanding", () => {
  const t = computeTotals({ amountCents: 1000, adjustments: [-300] });
  assert.strictEqual(t.adjustments, -300);
  assert.strictEqual(t.outstanding, 700);
});

test("adjustments combine with payments and credits", () => {
  const t = computeTotals({ amountCents: 1000, payments: [400], credits: [100], adjustments: [50, 50] });
  assert.strictEqual(t.adjustments, 100);
  assert.strictEqual(t.outstanding, 600); // 1000 + 100 - 400 - 100
});

test("a large discount cannot drive outstanding negative", () => {
  assert.strictEqual(computeTotals({ amountCents: 1000, adjustments: [-1500] }).outstanding, 0);
});

test("missing adjustments default to zero and preserve old behaviour", () => {
  const t = computeTotals({ amountCents: 1000, payments: [400] });
  assert.strictEqual(t.adjustments, 0);
  assert.strictEqual(t.outstanding, 600);
});

test("summary reports adjustments per status and nets them into outstanding", () => {
  const s = summarizeByStatus([
    { id: 1, status: "open", amount_cents: 1000, adjustments: [200] },
    { id: 2, status: "open", amount_cents: 500, adjustments: [-100], payments: [100] },
  ]);
  assert.strictEqual(s.open.count, 2);
  assert.strictEqual(s.open.adjustments, 100); // 200 + (-100)
  assert.strictEqual(s.open.outstanding, 1500); // 1200 + 300
});

test("summary leaves invoices unmutated and keeps status labels", () => {
  const invoices = [{ id: 1, status: "overdue", amount_cents: 500, adjustments: [25] }];
  const snapshot = JSON.parse(JSON.stringify(invoices));
  const s = summarizeByStatus(invoices);
  assert.deepStrictEqual(Object.keys(s), ["overdue"]);
  assert.strictEqual(s.overdue.outstanding, 525);
  assert.deepStrictEqual(invoices, snapshot);
});
