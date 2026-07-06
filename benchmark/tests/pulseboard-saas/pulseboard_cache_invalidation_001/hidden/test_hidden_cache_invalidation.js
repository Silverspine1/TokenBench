"use strict";

// Hidden tests: filtered-report cache invalidation (P5, frontier-hard).
// The cache key must depend on the whole filter and be independent of key
// order; cached results must not be mutable by callers; an invoice update must
// invalidate the cache; the cache must actually be used (a naive fix that
// recomputes every time is rejected); and two states must not share a cache.
// Per-case scoring via node:test.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { InvoiceState } = require(path.join(ws, "src", "state", "invoiceState.js"));
const { cacheKey } = require(path.join(ws, "src", "state", "cache.js"));

function sample() {
  return [
    { id: 1, status: "open", amount_cents: 100 },
    { id: 2, status: "paid", amount_cents: 200 },
    { id: 3, status: "open", amount_cents: 300 },
  ];
}

test("different filters do not collide", () => {
  const state = new InvoiceState(sample());
  const openCount = state.getFilteredReport({ status: "open" }).count;
  const paidCount = state.getFilteredReport({ status: "paid" }).count;
  assert.strictEqual(openCount, 2);
  assert.strictEqual(paidCount, 1);
});

test("same filter with different key order hits the cache", () => {
  const state = new InvoiceState(sample());
  state.getFilteredReport({ status: "open", offsetMinutes: 0 });
  state.getFilteredReport({ offsetMinutes: 0, status: "open" });
  assert.strictEqual(state.computeCount, 1, "key order should not change the cache key");
  assert.strictEqual(
    cacheKey({ status: "open", offsetMinutes: 0 }),
    cacheKey({ offsetMinutes: 0, status: "open" })
  );
});

test("filter key order never changes the cache key across three permutations", () => {
  const state = new InvoiceState(sample());
  const f1 = { status: "open", dueOnOrBefore: "2026-06-15", offsetMinutes: 0 };
  const f2 = { offsetMinutes: 0, status: "open", dueOnOrBefore: "2026-06-15" };
  const f3 = { dueOnOrBefore: "2026-06-15", offsetMinutes: 0, status: "open" };
  state.getFilteredReport(f1);
  state.getFilteredReport(f2);
  state.getFilteredReport(f3);
  assert.strictEqual(state.computeCount, 1, "reordered-but-equal filters must share one cache entry");
  assert.strictEqual(cacheKey(f1), cacheKey(f2));
  assert.strictEqual(cacheKey(f2), cacheKey(f3));
});

test("cacheKey distinguishes different values and different fields", () => {
  assert.notStrictEqual(cacheKey({ status: "open" }), cacheKey({ status: "paid" }));
  assert.notStrictEqual(cacheKey({ status: "open" }), cacheKey({ status: "open", dueOnOrBefore: "2026-06-15" }));
});

test("repeated identical query is served from cache, not recomputed", () => {
  const state = new InvoiceState(sample());
  state.getFilteredReport({ status: "open" });
  state.getFilteredReport({ status: "open" });
  state.getFilteredReport({ status: "open" });
  assert.strictEqual(state.computeCount, 1, "cache must not be bypassed");
  assert.strictEqual(state.hits, 2);
});

test("mutating a returned report does not corrupt the cache", () => {
  const state = new InvoiceState(sample());
  const first = state.getFilteredReport({ status: "open" });
  first.invoices.push({ id: 999 });
  first.count = -1;
  const second = state.getFilteredReport({ status: "open" });
  assert.strictEqual(second.count, 2);
  assert.strictEqual(second.invoices.length, 2);
});

test("mutating a nested invoice in a returned report does not corrupt the cache", () => {
  const state = new InvoiceState(sample());
  const first = state.getFilteredReport({ status: "open" });
  first.invoices[0].amountCents = -777;
  const second = state.getFilteredReport({ status: "open" });
  assert.notStrictEqual(second.invoices[0].amountCents, -777, "nested mutation leaked into cache");
});

test("updating an invoice invalidates the cache", () => {
  const state = new InvoiceState(sample());
  assert.strictEqual(state.getFilteredReport({ status: "open" }).count, 2);
  state.updateInvoice(1, { status: "paid" });
  assert.strictEqual(state.getFilteredReport({ status: "open" }).count, 1, "stale cached report returned");
});

test("update invalidates every cached filter, not just the queried one", () => {
  const state = new InvoiceState(sample());
  state.getFilteredReport({ status: "open" });
  state.getFilteredReport({ status: "paid" });
  state.updateInvoice(2, { status: "open" });
  assert.strictEqual(state.getFilteredReport({ status: "open" }).count, 3);
  assert.strictEqual(state.getFilteredReport({ status: "paid" }).count, 0);
});

test("two independent states do not share a cache", () => {
  const a = new InvoiceState(sample());
  const b = new InvoiceState([{ id: 1, status: "open", amount_cents: 1 }]);
  assert.strictEqual(a.getFilteredReport({ status: "open" }).count, 2);
  assert.strictEqual(b.getFilteredReport({ status: "open" }).count, 1);
});

test("a recompute after invalidation increments computeCount again", () => {
  const state = new InvoiceState(sample());
  state.getFilteredReport({ status: "open" });
  assert.strictEqual(state.computeCount, 1);
  state.updateInvoice(1, { status: "paid" });
  state.getFilteredReport({ status: "open" });
  assert.strictEqual(state.computeCount, 2, "post-invalidation query must recompute");
});
