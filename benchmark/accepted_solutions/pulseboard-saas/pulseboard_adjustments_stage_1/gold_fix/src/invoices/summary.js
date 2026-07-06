"use strict";

// Status summary with partial payments and credits. For each status it reports
// count plus gross/paid/outstanding/credited (cents). Invoices are normalized
// first and never mutated.

const { normalizeInvoices } = require("./schema");
const { computeTotals } = require("./totals");

function _emptyBucket() {
  return { count: 0, gross: 0, paid: 0, outstanding: 0, credited: 0, adjustments: 0 };
}

function summarizeByStatus(invoices) {
  const rows = normalizeInvoices(invoices);
  const out = {};
  for (const inv of rows) {
    const t = computeTotals(inv);
    const bucket = out[inv.status] || (out[inv.status] = _emptyBucket());
    bucket.count += 1;
    bucket.gross += t.gross;
    bucket.paid += t.paid;
    bucket.outstanding += t.outstanding;
    bucket.credited += t.credited;
    bucket.adjustments += t.adjustments;
  }
  return out;
}

module.exports = { summarizeByStatus };
