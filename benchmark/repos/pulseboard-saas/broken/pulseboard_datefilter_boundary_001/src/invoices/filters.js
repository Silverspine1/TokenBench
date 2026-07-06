"use strict";

// Invoice filtering. Always operates on the canonical (normalized) shape and
// returns a fresh list of normalized copies, so callers can never mutate the
// source invoices through the result.

const { normalizeInvoices } = require("./schema");
const { onOrBeforeLocal } = require("../shared/dates");

function filterInvoices(invoices, filter) {
  const f = filter || {};
  let rows = normalizeInvoices(invoices);

  if (f.status) {
    rows = rows.filter((r) => r.status === f.status);
  }
  if (f.dueOnOrBefore) {
    rows = rows.filter((r) => r.dueDate && r.dueDate.slice(0, 10) <= f.dueOnOrBefore);
  }
  return rows;
}

module.exports = { filterInvoices };
