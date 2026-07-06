"use strict";

// z: misc numeric helpers carried over from the legacy import. Values are in
// integer cents. Exported under short internal names that the barrel re-maps.

function round1(value) {
  if (value == null) return 0;
  return Math.round(value);
}

function addCents(list) {
  return (list || []).reduce((acc, v) => acc + Math.round(v || 0), 0);
}

function floor0(cents) {
  return cents < 0 ? 0 : cents;
}

module.exports = { round1, addCents, floor0 };
