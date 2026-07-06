"use strict";

const path = require("path");
const assert = require("assert");

const ws = process.env.TOKENBENCH_WORKSPACE;
const { paginate } = require(path.join(ws, "src", "pagination.js"));

const items = Array.from({ length: 10 }, (_, i) => i + 1);

// page=1 (1-based) returns the FIRST page, not the second.
assert.deepStrictEqual(paginate(items, 1, 3), [1, 2, 3], "page 1 must be the first rows");

// page=2 returns the next slice with no skipped or duplicated boundary rows.
assert.deepStrictEqual(paginate(items, 2, 3), [4, 5, 6], "page 2 boundary is wrong");

// Concatenating consecutive pages reproduces the rows contiguously.
const combined = paginate(items, 1, 4).concat(paginate(items, 2, 4));
assert.deepStrictEqual(combined, [1, 2, 3, 4, 5, 6, 7, 8], "pages must tile without gaps");

console.log("hidden OK");
