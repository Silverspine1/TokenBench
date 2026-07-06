"use strict";

// A small result cache keyed by a normalized filter. The key is derived from
// ALL filter fields and is independent of key insertion order, so two equal
// filters written in different orders hit the same entry. Stored values are
// deep-copied on the way in and out, so a cached result can never be mutated by
// a caller (and a caller's later mutation can never corrupt the cache).

function cacheKey(filter) {
  const f = filter || {};
  const keys = Object.keys(f).sort();
  return JSON.stringify(keys.map((k) => [k, f[k]]));
}

function _clone(value) {
  return JSON.parse(JSON.stringify(value));
}

class Cache {
  constructor() {
    this.store = new Map();
  }

  has(key) {
    return this.store.has(key);
  }

  get(key) {
    if (!this.store.has(key)) return undefined;
    return _clone(this.store.get(key));
  }

  set(key, value) {
    this.store.set(key, _clone(value));
  }

  clear() {
    this.store.clear();
  }
}

module.exports = { cacheKey, Cache };
