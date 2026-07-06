"use strict";

// Hidden tests: local business-date range boundary (P2).
// Date filtering uses the business calendar date derived from an explicit
// offset (minutes), not UTC and not the machine timezone. The end-of-day is
// inclusive. A lexicographic compare on the raw ISO string is wrong.
// Per-case scoring via node:test.

const { test } = require("node:test");
const assert = require("node:assert");
const path = require("path");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { onOrBeforeLocal, localBusinessDate } = require(path.join(ws, "src", "shared", "dates.js"));
const { filterInvoices } = require(path.join(ws, "src", "invoices", "filters.js"));

const CT = 120; // Cape Town, UTC+02:00
const NY = -300; // UTC-05:00

test("positive offset: instant after local midnight is excluded", () => {
  // 00:30 local on the 16th (UTC 22:30 on the 15th). Business date is the 16th.
  assert.strictEqual(localBusinessDate("2026-06-16T00:30:00+02:00", CT), "2026-06-16");
  assert.strictEqual(onOrBeforeLocal("2026-06-16T00:30:00+02:00", "2026-06-15", CT), false);
  // 23:30 local on the 15th stays on the 15th.
  assert.strictEqual(onOrBeforeLocal("2026-06-15T23:30:00+02:00", "2026-06-15", CT), true);
});

test("negative offset: business date reflects the offset", () => {
  // UTC 03:00 on the 16th is 22:00 on the 15th at UTC-5.
  assert.strictEqual(localBusinessDate("2026-06-16T03:00:00Z", NY), "2026-06-15");
  assert.strictEqual(onOrBeforeLocal("2026-06-16T03:00:00Z", "2026-06-15", NY), true);
  assert.strictEqual(onOrBeforeLocal("2026-06-16T06:00:00Z", "2026-06-15", NY), false);
});

test("end of day is inclusive to the last second", () => {
  assert.strictEqual(onOrBeforeLocal("2026-06-15T23:59:59+02:00", "2026-06-15", CT), true);
  assert.strictEqual(onOrBeforeLocal("2026-06-16T00:00:00+02:00", "2026-06-15", CT), false);
});

test("offset shifts the business date across a month boundary", () => {
  // 30 Jun 23:30 UTC at +02:00 is 01:30 on 1 Jul local -> business date July.
  assert.strictEqual(localBusinessDate("2026-06-30T23:30:00Z", CT), "2026-07-01");
  assert.strictEqual(onOrBeforeLocal("2026-06-30T23:30:00Z", "2026-06-30", CT), false);
});

test("offset shifts the business date backward across a month boundary", () => {
  // 1 Jul 01:00 UTC at UTC-5 is 30 Jun 20:00 local -> business date June.
  assert.strictEqual(localBusinessDate("2026-07-01T01:00:00Z", NY), "2026-06-30");
  assert.strictEqual(onOrBeforeLocal("2026-07-01T01:00:00Z", "2026-06-30", NY), true);
});

test("filter excludes by local date even when the ISO prefix says otherwise", () => {
  // ISO date prefix is the 16th, but at UTC business offset the instant lands on
  // the 15th, so it must be INCLUDED for a boundary of the 15th.
  const invoices = [
    { id: 1, status: "open", dueDate: "2026-06-16T03:00:00+05:00" }, // UTC 22:00 on 15th
    { id: 2, status: "open", dueDate: "2026-06-17T12:00:00+00:00" },
  ];
  const kept = filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: 0 });
  assert.deepStrictEqual(kept.map((i) => i.id), [1]);
});

test("filter honours a non-zero business offset", () => {
  // Instant is 15th 23:30 UTC. At +02:00 the business date is the 16th, so it is
  // EXCLUDED for a boundary of the 15th; at UTC it would be included.
  const invoices = [{ id: 1, status: "open", dueDate: "2026-06-15T23:30:00Z" }];
  assert.deepStrictEqual(
    filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: CT }).map((i) => i.id),
    []
  );
  assert.deepStrictEqual(
    filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: 0 }).map((i) => i.id),
    [1]
  );
});

test("invoice without a due date is excluded from a date-bounded filter", () => {
  const invoices = [
    { id: 1, status: "open" },
    { id: 2, status: "open", dueDate: "2026-06-10T10:00:00Z" },
  ];
  assert.deepStrictEqual(
    filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: 0 }).map((i) => i.id),
    [2]
  );
});

test("status and date filters compose", () => {
  const invoices = [
    { id: 1, status: "open", dueDate: "2026-06-10T10:00:00Z" },
    { id: 2, status: "paid", dueDate: "2026-06-10T10:00:00Z" },
    { id: 3, status: "open", dueDate: "2026-06-20T10:00:00Z" },
  ];
  const kept = filterInvoices(invoices, { status: "open", dueOnOrBefore: "2026-06-15", offsetMinutes: 0 });
  assert.deepStrictEqual(kept.map((i) => i.id), [1]);
});

test("date filtering does not mutate input", () => {
  const invoices = [{ id: 1, status: "open", dueDate: "2026-06-15T10:00:00+02:00" }];
  const snapshot = JSON.parse(JSON.stringify(invoices));
  filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: CT });
  assert.deepStrictEqual(invoices, snapshot);
});

test("offset selects a different kept set than a raw-UTC compare would", () => {
  // The offset must be applied inside the filter, not just available in dates.js.
  const invoices = [
    { id: 1, status: "open", dueDate: "2026-06-15T23:30:00Z" }, // UTC 15th / CT 16th
    { id: 2, status: "open", dueDate: "2026-06-14T10:00:00Z" }, // both on/before 15th
    { id: 3, status: "open", dueDate: "2026-06-16T12:00:00Z" }, // both after 15th
  ];
  const utc = filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: 0 }).map((i) => i.id);
  const ct = filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: CT }).map((i) => i.id);
  assert.deepStrictEqual(utc, [1, 2]);
  assert.deepStrictEqual(ct, [2], "offset not applied through the filter");
});

test("end-of-day stays inclusive through the filter at a business offset", () => {
  const invoices = [{ id: 1, status: "open", dueDate: "2026-06-15T23:59:59+02:00" }];
  assert.deepStrictEqual(
    filterInvoices(invoices, { dueOnOrBefore: "2026-06-15", offsetMinutes: CT }).map((i) => i.id),
    [1]
  );
});
