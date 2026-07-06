"use strict";

// Pulseboard SaaS — API/UI boundary normalization.
//
// The API returns raw invoices in snake_case with cents (amount_cents). The
// UI/export layer works in camelCase (amountCents). This module is the single
// boundary where the API representation is translated into the internal shape.

function normalizeInvoice(apiInvoice) {
  return {
    id: apiInvoice.id,
    status: apiInvoice.status,
    amount_cents: apiInvoice.amount_cents,
  };
}

function normalizeInvoices(apiInvoices) {
  return apiInvoices.map(normalizeInvoice);
}

module.exports = { normalizeInvoice, normalizeInvoices };
