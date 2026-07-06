"use strict";

// Hidden tests: API adapter backward compatibility (P4).
// Old flat responses and new nested responses must both arrive downstream as one
// canonical invoice shape, mixed batches included, a bare array or { invoices }
// envelope both accepted, a missing optional customer tolerated, and the source
// response never mutated. Per-case scoring via node:test.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { adaptInvoices } = require(path.join(ws, "src", "api", "invoicesApi.js"));
const { CANONICAL_FIELDS } = require(path.join(ws, "src", "invoices", "schema.js"));

function assertCanonical(inv) {
  for (const f of CANONICAL_FIELDS) {
    assert.ok(f in inv, "missing canonical field: " + f);
  }
}

test("old flat response normalizes", () => {
  const out = adaptInvoices({
    invoices: [{ id: 1, status: "paid", amount_cents: 10000, customer_name: "Acme" }],
  });
  assert.strictEqual(out[0].amountCents, 10000);
  assert.strictEqual(out[0].customerName, "Acme");
  assertCanonical(out[0]);
});

test("new nested response normalizes", () => {
  const out = adaptInvoices({
    invoices: [{ id: 2, status: "open", amount: { cents: 30000 }, customer: { name: "Initech" } }],
  });
  assert.strictEqual(out[0].amountCents, 30000);
  assert.strictEqual(out[0].customerName, "Initech");
  assertCanonical(out[0]);
});

test("bare array response (no envelope) is accepted", () => {
  const out = adaptInvoices([{ id: 7, status: "open", amount_cents: 50 }]);
  assert.strictEqual(out.length, 1);
  assert.strictEqual(out[0].amountCents, 50);
  assertCanonical(out[0]);
});

test("mixed batch yields uniform canonical shape and order", () => {
  const out = adaptInvoices([
    { id: 1, status: "paid", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "open", amount: { cents: 200 }, customer: { name: "B" } },
  ]);
  assert.strictEqual(out.length, 2);
  out.forEach(assertCanonical);
  assert.deepStrictEqual(out.map((i) => i.amountCents), [100, 200]);
  assert.deepStrictEqual(out.map((i) => i.id), [1, 2]);
});

test("missing optional customer does not throw", () => {
  const out = adaptInvoices({
    invoices: [{ id: 3, status: "open", amount: { cents: 5000 }, customer: null }],
  });
  assert.strictEqual(out[0].customerName, null);
  assertCanonical(out[0]);
});

test("missing amount on a nested item normalizes to 0", () => {
  const out = adaptInvoices([{ id: 4, status: "open", customer: { name: "Z" } }]);
  assert.strictEqual(out[0].amountCents, 0);
  assertCanonical(out[0]);
});

test("empty / malformed responses yield an empty list, not a throw", () => {
  assert.deepStrictEqual(adaptInvoices(null), []);
  assert.deepStrictEqual(adaptInvoices({}), []);
  assert.deepStrictEqual(adaptInvoices({ invoices: [] }), []);
});

test("canonical field set is stable across shapes", () => {
  const out = adaptInvoices([
    { id: 1, status: "paid", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "open", amount: { cents: 200 }, customer: { name: "B" } },
  ]);
  const keysA = Object.keys(out[0]).sort();
  const keysB = Object.keys(out[1]).sort();
  assert.deepStrictEqual(keysA, keysB);
});

test("adapter does not mutate the raw response", () => {
  const raw = { invoices: [{ id: 1, status: "open", amount: { cents: 200 }, customer: { name: "B" } }] };
  const snapshot = JSON.parse(JSON.stringify(raw));
  adaptInvoices(raw);
  assert.deepStrictEqual(raw, snapshot);
});
