"use strict";

// m2: CSV emission for the filtered invoice set, plus the column list. Pulls the
// filtering from m1. Short internal export names; the barrel re-maps them.

const { listFilter } = require("./m1");
const { toCsv } = require("./shared/csv");

const COLS = ["id", "status", "amountCents", "customerName"];

function dumpCsv(invoices, filter) {
  const rows = listFilter(invoices, filter);
  return toCsv(rows, COLS);
}

module.exports = { dumpCsv, COLS };
