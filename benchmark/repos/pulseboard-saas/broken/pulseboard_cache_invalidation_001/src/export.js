"use strict";

// Pulseboard SaaS — invoice CSV export.

function selectInvoices(invoices, filter) {
  if (!filter || !filter.status) {
    return invoices.slice();
  }
  return invoices.filter((inv) => inv.status === filter.status);
}

function exportInvoicesToCsv(invoices, filter) {
  const selected = selectInvoices(invoices, filter);
  const header = "id,amount,status";
  const lines = selected.map((i) => `${i.id},${i.amount},${i.status}`);
  return [header, ...lines].join("\n");
}

module.exports = { selectInvoices, exportInvoicesToCsv };
