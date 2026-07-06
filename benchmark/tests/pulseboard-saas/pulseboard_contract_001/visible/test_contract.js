"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { normalizeInvoice } = require(path.join(ws, "src", "contract.js"));

// Pass-through fields survive normalization.
const out = normalizeInvoice({ id: 7, status: "paid", amount_cents: 1299 });
assert.strictEqual(out.id, 7);
assert.strictEqual(out.status, "paid");

console.log("visible OK");
