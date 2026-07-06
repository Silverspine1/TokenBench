"use strict";

// m3: per-invoice money totals AND the by-status rollup, kept together from the
// legacy import. Short internal export names; the barrel re-maps them.

const { addCents, floor0 } = require("./lib/z");
const { toCanonical } = require("./m1");

function lineTotals(invoice) {
  const gross = invoice.amountCents || 0;
  const paid = addCents(invoice.payments || []);
  const credited = addCents(invoice.credits || []);
  const outstanding = floor0(gross - paid - credited);
  return { gross, paid, credited, outstanding };
}

function _emptyBucket() {
  return { count: 0, gross: 0, paid: 0, outstanding: 0, credited: 0 };
}

function rollup(invoices) {
  const rows = toCanonical(invoices);
  const out = {};
  for (const inv of rows) {
    const t = lineTotals(inv);
    const bucket = out[inv.status] || (out[inv.status] = _emptyBucket());
    bucket.count += 1;
    bucket.gross += t.gross;
    bucket.paid += t.paid;
    bucket.outstanding += t.outstanding;
    bucket.credited += t.credited;
  }
  return out;
}

module.exports = { lineTotals, rollup };
