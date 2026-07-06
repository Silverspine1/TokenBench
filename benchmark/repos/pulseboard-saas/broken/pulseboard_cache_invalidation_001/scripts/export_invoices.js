"use strict";

// Tiny example entry point: load sample invoices and print a CSV export.

const path = require("path");
const fs = require("fs");

const { exportInvoicesToCsv } = require(path.join(__dirname, "..", "src", "export.js"));

const invoicesPath = path.join(__dirname, "..", "fixtures", "invoices.json");
const invoices = JSON.parse(fs.readFileSync(invoicesPath, "utf8"));

const csv = exportInvoicesToCsv(invoices, { status: "paid" });
console.log(csv);
