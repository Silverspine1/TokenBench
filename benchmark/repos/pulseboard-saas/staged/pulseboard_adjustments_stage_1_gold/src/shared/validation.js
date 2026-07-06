"use strict";

// Light validation helpers shared across modules.

function isNonEmptyString(v) {
  return typeof v === "string" && v.length > 0;
}

function isFiniteNumber(v) {
  return typeof v === "number" && Number.isFinite(v);
}

module.exports = { isNonEmptyString, isFiniteNumber };
