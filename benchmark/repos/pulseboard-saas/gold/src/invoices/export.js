"use strict";

// CSV export of the filtered invoice set. Export reuses the same filter as the
// dashboard so the exported rows are exactly the filtered set - the full set,
// not the currently visible page. Source invoices are never mutated.

const { filterInvoices } = require("./filters");
const { toCsv } = require("../shared/csv");

const COLUMNS = ["id", "status", "amountCents", "customerName"];

function exportFilteredToCsv(invoices, filter) {
  const rows = filterInvoices(invoices, filter);
  return toCsv(rows, COLUMNS);
}

module.exports = { exportFilteredToCsv, COLUMNS };
