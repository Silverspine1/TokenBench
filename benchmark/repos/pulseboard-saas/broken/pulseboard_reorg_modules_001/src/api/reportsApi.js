"use strict";

// Report assembly over the canonical invoice shape.

const { filterInvoices, summarizeByStatus } = require("../m4");

function buildReport(invoices, filter) {
  const filtered = filterInvoices(invoices, filter);
  return {
    count: filtered.length,
    invoices: filtered,
    summary: summarizeByStatus(filtered),
  };
}

module.exports = { buildReport };
