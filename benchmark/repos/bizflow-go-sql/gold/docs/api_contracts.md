# API contracts

## GET /reports/revenue?tenant=<id>

Returns the tenant revenue summary:

```json
{
  "tenant_id": "t_acme",
  "rows": [
    { "invoice_id": "inv-1001", "customer": "North Hardware",
      "status": "paid", "total_cents": 5000, "paid_cents": 5000, "due_cents": 0 }
  ],
  "total_cents": 0,
  "paid_cents": 0,
  "due_cents": 0
}
```

Field names are part of the contract and must not change.

## POST /invoices

Body:

```json
{ "tenant_id": "t_acme", "customer": "North Hardware", "issued_at": "2026-02-01",
  "lines": [ { "sku": "WIDGET", "quantity": 5, "unit_cents": 500 } ] }
```

Responds `201` with the created invoice, `409` when stock is insufficient, and
`400` for an unknown product or an empty invoice.

## Invoice listing and paging

A tenant's invoices are listed in a fixed, total order: by `issued_at`, and for
invoices that share an issue date, by invoice `id`. This order is stable, so two
invoices issued on the same date always come back in the same id order no matter
how they were inserted.

Paging walks that ordered list. Starting at the first page and following each
page's cursor to the next visits every invoice exactly once, in order, with none
skipped or repeated at a page boundary. When the number of invoices is an exact
multiple of the page size, paging ends cleanly on the last full page: there is no
extra empty page. A page requested past the end is empty, and a page size larger
than the list returns the whole list.
