"use strict";

// Hidden tests: filter / pagination / export contract (P1).
// Filtering, pagination, and export must all operate on the same normalized
// filtered set, export must emit every filtered row (not just one page), the
// source invoices must not be mutated, ordering must be preserved, and
// amount_cents / amount.cents / amountCents must all normalize to the same
// canonical amount. Per-case scoring via node:test.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { filterInvoices } = require(path.join(ws, "src", "invoices", "filters.js"));
const { paginate } = require(path.join(ws, "src", "invoices", "pagination.js"));
const { exportFilteredToCsv } = require(path.join(ws, "src", "invoices", "export.js"));
const { normalizeInvoice } = require(path.join(ws, "src", "invoices", "schema.js"));

function sampleInvoices() {
  return [
    { id: 1, status: "open", amount_cents: 100, customer_name: "A" },
    { id: 2, status: "paid", amount_cents: 200, customer_name: "B" },
    { id: 3, status: "open", amount: { cents: 300 }, customer: { name: "C" } },
    { id: 4, status: "open", amount_cents: 400, customer_name: "D" },
    { id: 5, status: "paid", amount_cents: 500, customer_name: "E" },
  ];
}

function csvIds(csv) {
  return csv
    .split("\n")
    .slice(1)
    .filter((l) => l.length)
    .map((l) => Number(l.split(",")[0]));
}

test("export emits every filtered row, not just the visible page", () => {
  const invoices = sampleInvoices();
  const filtered = filterInvoices(invoices, { status: "open" });
  const csv = exportFilteredToCsv(invoices, { status: "open" });
  assert.strictEqual(filtered.length, 3, "filter should match 3 open invoices");
  assert.strictEqual(csvIds(csv).length, filtered.length, "export must include all filtered rows");
  assert.deepStrictEqual(csvIds(csv).sort(), [1, 3, 4]);
});

test("pagination slices the filtered set in filtered order", () => {
  const invoices = sampleInvoices();
  const filtered = filterInvoices(invoices, { status: "open" });
  assert.deepStrictEqual(paginate(filtered, 1, 2).map((i) => i.id), [1, 3]);
  assert.deepStrictEqual(paginate(filtered, 2, 2).map((i) => i.id), [4]);
});

test("pagination preserves source order, not id-sorted order", () => {
  // A fix that sorts by id would still pass id checks above; this catches a
  // reorder by interleaving statuses so source order != sorted order.
  const invoices = [
    { id: 9, status: "open", amount_cents: 1, customer_name: "Z" },
    { id: 2, status: "open", amount_cents: 1, customer_name: "Y" },
    { id: 7, status: "open", amount_cents: 1, customer_name: "X" },
  ];
  const filtered = filterInvoices(invoices, { status: "open" });
  assert.deepStrictEqual(filtered.map((i) => i.id), [9, 2, 7]);
  assert.deepStrictEqual(paginate(filtered, 1, 2).map((i) => i.id), [9, 2]);
});

test("page beyond the end is empty; page size larger than set returns all", () => {
  const filtered = filterInvoices(sampleInvoices(), { status: "open" });
  assert.deepStrictEqual(paginate(filtered, 99, 2), []);
  assert.deepStrictEqual(paginate(filtered, 1, 100).map((i) => i.id), [1, 3, 4]);
});

test("source invoices are not mutated by filter/export/paginate", () => {
  const invoices = sampleInvoices();
  const snapshot = JSON.parse(JSON.stringify(invoices));
  filterInvoices(invoices, { status: "open" });
  exportFilteredToCsv(invoices, { status: "open" });
  paginate(filterInvoices(invoices, { status: "open" }), 1, 2);
  assert.deepStrictEqual(invoices, snapshot, "inputs changed after filter/export/paginate");
});

test("amount_cents / amount.cents / amountCents all normalize equally", () => {
  assert.strictEqual(normalizeInvoice({ id: 1, status: "open", amount_cents: 1299 }).amountCents, 1299);
  assert.strictEqual(normalizeInvoice({ id: 2, status: "open", amount: { cents: 1299 } }).amountCents, 1299);
  assert.strictEqual(normalizeInvoice({ id: 3, status: "open", amountCents: 1299 }).amountCents, 1299);
});

test("nested-amount invoice carries its amount through the export", () => {
  const csv = exportFilteredToCsv(sampleInvoices(), { status: "open" });
  const line = csv.split("\n").find((l) => l.startsWith("3,"));
  assert.ok(line, "row 3 missing from export");
  assert.ok(line.includes(",300,"), "nested amount missing from export: " + line);
});

test("missing amount normalizes to 0 and exports as 0", () => {
  const inv = normalizeInvoice({ id: 8, status: "open" });
  assert.strictEqual(inv.amountCents, 0);
  const csv = exportFilteredToCsv([{ id: 8, status: "open" }], { status: "open" });
  const line = csv.split("\n").find((l) => l.startsWith("8,"));
  assert.ok(line.includes(",0,"), "missing amount should export as 0: " + line);
});

test("empty filter returns and exports the whole normalized set", () => {
  const invoices = sampleInvoices();
  assert.strictEqual(filterInvoices(invoices, {}).length, 5);
  assert.strictEqual(csvIds(exportFilteredToCsv(invoices, {})).length, 5);
});

test("filter, export, and pagination agree on the same id set", () => {
  const invoices = sampleInvoices();
  const filtered = filterInvoices(invoices, { status: "open" }).map((i) => i.id).sort();
  const exported = csvIds(exportFilteredToCsv(invoices, { status: "open" })).sort();
  const paged = []
    .concat(paginate(filterInvoices(invoices, { status: "open" }), 1, 2).map((i) => i.id))
    .concat(paginate(filterInvoices(invoices, { status: "open" }), 2, 2).map((i) => i.id))
    .sort();
  assert.deepStrictEqual(exported, filtered);
  assert.deepStrictEqual(paged, filtered);
});
