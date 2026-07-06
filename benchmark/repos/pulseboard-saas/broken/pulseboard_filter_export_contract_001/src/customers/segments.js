"use strict";

// Group customers into spend tiers (cents thresholds).

function segmentBySpend(customers) {
  const out = { low: [], mid: [], high: [] };
  for (const c of customers || []) {
    const spend = c.lifetimeSpendCents || 0;
    if (spend >= 1000000) out.high.push(c.id);
    else if (spend >= 100000) out.mid.push(c.id);
    else out.low.push(c.id);
  }
  return out;
}

module.exports = { segmentBySpend };
