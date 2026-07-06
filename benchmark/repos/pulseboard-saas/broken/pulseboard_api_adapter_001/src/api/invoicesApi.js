"use strict";

// Adapter boundary for the invoices API. Responses may be a bare array or
// { invoices: [...] }, and each item may be in the old flat shape or the new
// nested shape. Everything downstream of this boundary receives one canonical
// invoice shape.

const { normalizeInvoices } = require("../invoices/schema");

function adaptInvoices(rawResponse) {
  let list;
  if (Array.isArray(rawResponse)) {
    list = rawResponse;
  } else if (rawResponse && Array.isArray(rawResponse.invoices)) {
    list = rawResponse.invoices;
  } else {
    list = [];
  }
  return list;
}

module.exports = { adaptInvoices };
