"use strict";

// Pulseboard SaaS — filter invoices by local due date.
//
// Invoices carry an ISO 8601 dueDate that includes its UTC offset, e.g.
// "2026-06-15T23:30:00-05:00". The calendar date a customer sees ("due on the
// 15th") is the LOCAL date, i.e. the date portion as written.

function localDueDate(invoice) {
  return new Date(invoice.dueDate).toISOString().slice(0, 10);
}

function invoicesDueOnOrBefore(invoices, endDateLocal) {
  return invoices.filter((inv) => localDueDate(inv) <= endDateLocal);
}

module.exports = { invoicesDueOnOrBefore, localDueDate };
