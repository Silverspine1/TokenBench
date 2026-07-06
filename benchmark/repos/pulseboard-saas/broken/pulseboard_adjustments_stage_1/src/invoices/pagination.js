"use strict";

// Page slicing. 1-based page index. Returns a slice (does not mutate input).

function paginate(items, page, pageSize) {
  const p = Math.max(1, page | 0);
  const size = Math.max(1, pageSize | 0);
  const start = (p - 1) * size;
  return items.slice(start, start + size);
}

module.exports = { paginate };
