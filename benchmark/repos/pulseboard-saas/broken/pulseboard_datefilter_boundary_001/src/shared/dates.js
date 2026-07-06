"use strict";

// Business-local date handling. Invoice timestamps are absolute (ISO 8601 with
// their own offset). The dashboard groups invoices by the *business* calendar
// date, which depends on the business timezone offset (in minutes), NOT on the
// machine's local timezone. All comparisons use explicit offsets so results are
// deterministic regardless of where the code runs.

function _epochMs(iso) {
  return Date.parse(iso);
}

function localBusinessDate(iso, offsetMinutes) {
  // Shift the absolute instant into the business timezone, then read the
  // calendar date there.
  const ms = _epochMs(iso);
  const d = new Date(ms);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function onOrBeforeLocal(iso, boundaryDate, offsetMinutes) {
  // boundaryDate is a 'YYYY-MM-DD' business date; the day is inclusive.
  // Lexicographic comparison is correct for zero-padded ISO dates.
  return localBusinessDate(iso, offsetMinutes) <= boundaryDate;
}

module.exports = { localBusinessDate, onOrBeforeLocal };
