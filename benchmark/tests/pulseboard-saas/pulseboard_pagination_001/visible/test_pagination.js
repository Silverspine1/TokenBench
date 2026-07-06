"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { paginate } = require(path.join(ws, "src", "pagination.js"));

const items = Array.from({ length: 10 }, (_, i) => i + 1);

// A page never exceeds pageSize and is always an array.
const page = paginate(items, 1, 5);
assert.ok(Array.isArray(page), "expected an array");
assert.strictEqual(page.length, 5, "page length should equal pageSize");

console.log("visible OK");
