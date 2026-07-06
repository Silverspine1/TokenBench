# Dashboard behavior

## Filter / pagination / export

The dashboard, the CSV export, and pagination must all operate on the **same
normalized, filtered set** of invoices:

* Filtering normalizes invoices to the canonical shape and returns fresh copies;
  the source invoices are never mutated.
* Pagination slices the **filtered** list (filtered order, 1-based pages).
* Export writes **every** filtered row - the full filtered set, not just the
  page currently visible on screen.

## Business dates

Date-range filters use the **business** calendar date, derived from an explicit
timezone offset (in minutes). Two invoices at the same instant can fall on
different business dates under different offsets; the end-of-day boundary is
inclusive.

## Caching

Filtered reports are cached by the full filter. An identical query (even with
the filter object's keys in a different order) is served from the cache. Any
change to an invoice invalidates the cache so a stale report is never returned.
