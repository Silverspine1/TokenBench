"use strict";

// Minimal RFC-4180-ish CSV writer. Pure: never mutates its inputs.

function escapeField(value) {
  const s = String(value == null ? "" : value);
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function toCsv(rows, columns) {
  const header = columns.join(",");
  const lines = rows.map((r) => columns.map((c) => escapeField(r[c])).join(","));
  return [header, ...lines].join("\n");
}

module.exports = { toCsv, escapeField };
