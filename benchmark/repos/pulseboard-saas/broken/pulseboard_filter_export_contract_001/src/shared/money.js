"use strict";

// Money is represented in integer cents everywhere. These helpers keep the
// arithmetic in cents so no floating-point drift creeps into totals.

function toCents(value) {
  if (value == null) return 0;
  return Math.round(value);
}

function sumCents(list) {
  return (list || []).reduce((acc, v) => acc + Math.round(v || 0), 0);
}

function clampNonNegative(cents) {
  return cents < 0 ? 0 : cents;
}

module.exports = { toCents, sumCents, clampNonNegative };
