"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { normalizeInvoice, normalizeInvoices } = require(path.join(ws, "src", "contract.js"));

// The boundary maps amount_cents -> amountCents and drops the raw snake_case
// key. A one-off patch that leaves amount_cents in place is rejected.
const out = normalizeInvoice({ id: 7, status: "paid", amount_cents: 1299 });
assert.strictEqual(out.amountCents, 1299, "amount_cents must map to amountCents");
assert.ok(!("amount_cents" in out), "raw amount_cents must not leak through the boundary");

// Works for a list of invoices, normalizing every element.
const list = normalizeInvoices([
  { id: 1, status: "open", amount_cents: 500 },
  { id: 2, status: "paid", amount_cents: 999 },
]);
assert.deepStrictEqual(
  list.map((i) => i.amountCents),
  [500, 999],
  "normalizeInvoices must normalize every element",
);
assert.ok(list.every((i) => !("amount_cents" in i)), "raw key leaked in list normalization");

console.log("hidden OK");
