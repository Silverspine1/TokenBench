"use strict";

// Per-invoice money totals, all in integer cents.
//
//   gross       = invoice amount
//   paid        = sum of payments
//   refunds     = sum of refunds returned to the customer
//   netPaid     = paid - refunds (money the business actually kept)
//   credited    = sum of credit memos
//   adjustments = sum of manual adjustments (signed: + surcharge, - discount)
//   outstanding = max(0, gross + adjustments - netPaid - credited)

const { sumCents, clampNonNegative } = require("../shared/money");

function computeTotals(invoice) {
  const gross = invoice.amountCents || 0;
  const paid = sumCents(invoice.payments || []);
  const refunds = sumCents(invoice.refunds || []);
  const netPaid = paid - refunds;
  const credited = sumCents(invoice.credits || []);
  const adjustments = sumCents(invoice.adjustments || []);
  const outstanding = clampNonNegative(gross + adjustments - netPaid - credited);
  return { gross, paid, refunds, netPaid, credited, adjustments, outstanding };
}

module.exports = { computeTotals };
