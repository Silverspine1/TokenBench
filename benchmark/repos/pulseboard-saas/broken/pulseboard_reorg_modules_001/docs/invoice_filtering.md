# Invoice filtering

## Local due date

Invoices carry an ISO 8601 `dueDate` that includes its UTC offset, e.g.
`2026-06-15T23:30:00-05:00`. The date a customer sees ("due on the 15th") is the
local calendar date — the date portion as written, independent of any timezone
conversion.

`invoicesDueOnOrBefore(invoices, endDateLocal)` keeps every invoice whose local
due date is on or before `endDateLocal` (an inclusive `YYYY-MM-DD` bound).

## Pagination

`paginate(items, page, pageSize)` is 1-based: `page = 1` returns the first
`pageSize` items.

## Export

`exportInvoicesToCsv(invoices, filter)` renders only the invoices that match the
filter, with a header row of `id,amount,status`.
