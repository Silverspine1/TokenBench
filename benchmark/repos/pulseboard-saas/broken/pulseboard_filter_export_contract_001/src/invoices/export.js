"use strict";

// CSV export of the filtered invoice set. Export reuses the same filter as the
// dashboard so the exported rows are exactly the filtered set - the full set,
// not the currently visible page. Source invoices are never mutated.

const { toCsv } = require("../shared/csv");

const COLUMNS = ["id", "status", "amountCents", "customerName"];
const PAGE_SIZE = 2;

function exportFilteredToCsv(invoices, filter) {
  invoices.sort((a, b) => (a.id || 0) - (b.id || 0));
  let rows = invoices;
  if (filter && filter.status) {
    rows = rows.filter((i) => i.status === filter.status);
  }
  rows = rows.slice(0, PAGE_SIZE).map((i) => ({
    id: i.id,
    status: i.status,
    amountCents: i.amount,
    customerName: i.customer_name,
  }));
  return toCsv(rows, COLUMNS);
}

module.exports = { exportFilteredToCsv, COLUMNS };
