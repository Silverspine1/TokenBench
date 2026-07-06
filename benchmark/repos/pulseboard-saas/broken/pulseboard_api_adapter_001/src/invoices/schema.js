"use strict";

// Canonical invoice shape. API responses arrive in two shapes:
//   * flat  : { id, status, amount_cents | amountCents, customer_name, due_date }
//   * nested: { id, status, amount: { cents }, customer: { name }, dueDate }
// normalizeInvoice maps either onto ONE canonical object and never mutates the
// input. Every downstream module (filter, export, summary, report) consumes the
// canonical shape so they cannot disagree on field names.

const CANONICAL_FIELDS = [
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
  return 0;
}

function _customerName(raw) {
  if (raw.customerName != null) return raw.customerName;
  if (raw.customer_name != null) return raw.customer_name;
  return null;
}

function normalizeInvoice(raw) {
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

function normalizeInvoices(list) {
  return (list || []).map(normalizeInvoice);
}

module.exports = { CANONICAL_FIELDS, normalizeInvoice, normalizeInvoices };
