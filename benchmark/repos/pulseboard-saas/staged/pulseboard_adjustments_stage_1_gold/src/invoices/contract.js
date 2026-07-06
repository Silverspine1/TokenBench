"use strict";

// The canonical invoice contract that downstream modules rely on.

const { CANONICAL_FIELDS } = require("./schema");

function isCanonical(invoice) {
  if (!invoice || typeof invoice !== "object") return false;
  return CANONICAL_FIELDS.every((f) => f in invoice);
}

module.exports = { CANONICAL_FIELDS, isCanonical };
