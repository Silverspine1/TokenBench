"use strict";

// Pulseboard SaaS — invoice list pagination.

function paginate(items, page, pageSize) {
  // `page` is 1-based: page=1 returns the first `pageSize` items.
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

module.exports = { paginate };
