"use strict";

// Per-invoice money totals, all in integer cents.
//
//   gross       = invoice amount
//   paid        = sum of payments
//   credited    = sum of credit memos
//   outstanding = max(0, gross - paid - credited)   (overpayment clamps to 0)

const { sumCents, clampNonNegative } = require("../shared/money");

function computeTotals(invoice) {
  const gross = invoice.amountCents || 0;
  const paid = sumCents(invoice.payments || []);
  const credited = sumCents(invoice.credits || []);
  const outstanding = gross - paid;
  return { gross, paid, credited, outstanding };
}

module.exports = { computeTotals };
