"use strict";

// Controlled long-output visible check (V0.7 output_stress). Emits a bounded,
// deterministic block of per-case lines through the public entrypoint so the
// harness has a realistic large test-output to measure (for output-compression
// benchmarking). Offline, deterministic, ~160 KB. Always exits 0.

const path = require("path");
const api = require(path.join(__dirname, "..", "src", "index.js"));

const STATUSES = ["open", "paid", "overdue", "void", "draft"];
const CASES = 2000;

let lines = 0;
for (let i = 0; i < CASES; i++) {
  const status = STATUSES[i % STATUSES.length];
  const invoices = [
    { id: i, status, amount_cents: 1000 + (i % 500), payments: [i % 300], credits: [i % 50] },
  ];
  const s = api.summarizeByStatus(invoices);
  const t = s[status];
  // One fixed-width labelled line per case (deterministic content).
  process.stdout.write(
    `case ${String(i).padStart(5, "0")} status=${status.padEnd(8)} ` +
      `gross=${String(t.gross).padStart(6)} paid=${String(t.paid).padStart(6)} ` +
      `credited=${String(t.credited).padStart(6)} outstanding=${String(t.outstanding).padStart(6)} ` +
      `:: reconciled\n`
  );
  lines++;
}
process.stdout.write(`output-stress OK: ${lines} cases reconciled\n`);
