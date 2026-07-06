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
    const offset = f.offsetMinutes || 0;
    rows = rows.filter((r) => r.dueDate && onOrBeforeLocal(r.dueDate, f.dueOnOrBefore, offset));
  }
  return rows;
}

module.exports = { filterInvoices };
