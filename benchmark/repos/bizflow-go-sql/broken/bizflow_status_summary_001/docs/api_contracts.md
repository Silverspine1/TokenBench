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
