"use strict";

// Per-invoice money totals, all in integer cents.
//
//   gross       = invoice amount
//   paid        = sum of payments
//   credited    = sum of credit memos
//   adjustments = sum of manual adjustments (signed: + surcharge, - discount)
//   outstanding = max(0, gross + adjustments - paid - credited)

const { sumCents, clampNonNegative } = require("../shared/money");

function computeTotals(invoice) {
  const gross = invoice.amountCents || 0;
  const paid = sumCents(invoice.payments || []);
  const credited = sumCents(invoice.credits || []);
  const adjustments = sumCents(invoice.adjustments || []);
  const outstanding = clampNonNegative(gross + adjustments - paid - credited);
  return { gross, paid, credited, adjustments, outstanding };
}

module.exports = { computeTotals };
