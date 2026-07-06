"use strict";

// Pulseboard SaaS — invoice CSV export.

function selectInvoices(invoices, filter) {
  // Return the invoices to include in the export.
  return invoices.slice();
}

function exportInvoicesToCsv(invoices, filter) {
  const selected = selectInvoices(invoices, filter);
  const header = "id,amount,status";
  const lines = selected.map((i) => `${i.id},${i.amount},${i.status}`);
  return [header, ...lines].join("\n");
}

module.exports = { selectInvoices, exportInvoicesToCsv };
