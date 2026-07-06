"use strict";

// Holds the invoice set and caches filtered reports. A filtered report is
// cached under the full filter key; an identical query is served from the cache
// (no recompute), but any change to the underlying invoices invalidates it so
// stale results are never returned.

const { cacheKey, Cache } = require("./cache");
const { buildReport } = require("../api/reportsApi");
const { normalizeInvoices } = require("../m4");

class InvoiceState {
  constructor(invoices) {
    this.invoices = normalizeInvoices(invoices);
    this.cache = new Cache();
    this.computeCount = 0;
    this.hits = 0;
  }

  getFilteredReport(filter) {
    const key = cacheKey(filter);
    if (this.cache.has(key)) {
      this.hits += 1;
      return this.cache.get(key);
    }
    this.computeCount += 1;
    const report = buildReport(this.invoices, filter);
    this.cache.set(key, report);
    return this.cache.get(key);
  }

  updateInvoice(id, patch) {
    this.invoices = this.invoices.map((inv) =>
      inv.id === id ? Object.assign({}, inv, patch) : inv
    );
    // Underlying data changed: drop cached reports so they cannot go stale.
    this.cache.clear();
  }
}

module.exports = { InvoiceState };
