"use strict";

// Pulseboard SaaS — invoice status summary.

function summarizeByStatus(invoices) {
  // Counts and total amount per status. Does not mutate the input array.
  const summary = {};
  for (const inv of invoices) {
    if (!summary[inv.status]) {
      summary[inv.status] = { count: 0, total: 0 };
    }
    summary[inv.status].count += 1;
    summary[inv.status].total += inv.amount;
  }
  return summary;
}

module.exports = { summarizeByStatus };
