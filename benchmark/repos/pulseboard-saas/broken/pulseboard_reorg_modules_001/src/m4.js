"use strict";

// m4: a compatibility barrel left by the legacy import. It maps the short
// internal names in m1/m2/m3/z onto the public names the rest of the app uses.
// Everything outside this cluster imports from here.

const m1 = require("./m1");
const m2 = require("./m2");
const m3 = require("./m3");
const z = require("./lib/z");

module.exports = {
  normalizeInvoice: m1.oneCanonical,
  normalizeInvoices: m1.toCanonical,
  CANONICAL_FIELDS: m1.FIELDS,
  filterInvoices: m1.listFilter,
  exportFilteredToCsv: m2.dumpCsv,
  COLUMNS: m2.COLS,
  computeTotals: m3.lineTotals,
  summarizeByStatus: m3.rollup,
  toCents: z.round1,
  sumCents: z.addCents,
  clampNonNegative: z.floor0,
};
