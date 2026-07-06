"use strict";

// Customer filtering. Note: this is a *different* filter from invoices/filters
// despite the similar name - it matches on customer fields, not invoice fields.

function filterCustomers(customers, filter) {
  const f = filter || {};
  let rows = (customers || []).map((c) => Object.assign({}, c));
  if (f.region) {
    rows = rows.filter((c) => c.region === f.region);
  }
  if (f.active != null) {
    rows = rows.filter((c) => Boolean(c.active) === Boolean(f.active));
  }
  return rows;
}

module.exports = { filterCustomers };
