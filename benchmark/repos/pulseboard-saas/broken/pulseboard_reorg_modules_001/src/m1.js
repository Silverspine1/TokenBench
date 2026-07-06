"use strict";

// m1: a grab-bag from the legacy import. It holds the canonical invoice shape
// mapping AND the list filtering. Exported under short internal names; the
// barrel (m4) maps them back to the public names callers expect.

const { onOrBeforeLocal } = require("./shared/dates");

const FIELDS = [
  "id",
  "status",
  "amountCents",
  "customerName",
  "dueDate",
  "payments",
  "credits",
];

function _amountCents(raw) {
  if (raw.amountCents != null) return raw.amountCents;
  if (raw.amount_cents != null) return raw.amount_cents;
  if (raw.amount && raw.amount.cents != null) return raw.amount.cents;
  return 0;
}

function _customerName(raw) {
  if (raw.customerName != null) return raw.customerName;
  if (raw.customer_name != null) return raw.customer_name;
  if (raw.customer && raw.customer.name != null) return raw.customer.name;
  return null;
}

function oneCanonical(raw) {
  return {
    id: raw.id,
    status: raw.status,
    amountCents: _amountCents(raw),
    customerName: _customerName(raw),
    dueDate: raw.dueDate != null ? raw.dueDate : raw.due_date != null ? raw.due_date : null,
    payments: Array.isArray(raw.payments) ? raw.payments.slice() : [],
    credits: Array.isArray(raw.credits) ? raw.credits.slice() : [],
  };
}

function toCanonical(list) {
  return (list || []).map(oneCanonical);
}

function listFilter(invoices, filter) {
  const f = filter || {};
  let rows = toCanonical(invoices);
  if (f.status) {
    rows = rows.filter((r) => r.status === f.status);
  }
  if (f.dueOnOrBefore) {
    const offset = f.offsetMinutes || 0;
    rows = rows.filter((r) => r.dueDate && onOrBeforeLocal(r.dueDate, f.dueOnOrBefore, offset));
  }
  return rows;
}

module.exports = { FIELDS, oneCanonical, toCanonical, listFilter };
