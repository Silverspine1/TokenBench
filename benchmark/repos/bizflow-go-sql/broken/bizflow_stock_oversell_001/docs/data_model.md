# Data model

Every record belongs to exactly one tenant.

## tenants
- `id`, `name`

## products
- `tenant_id`, `sku`, `name`, `on_hand`, `reserved`
- Available stock is `on_hand - reserved`.

## invoices
- `id`, `tenant_id`, `customer`, `status` (`open`, `paid`, `void`), `issued_at`
- The stored `total_cents` is the sum of the invoice's line totals.

## payments
- `id`, `invoice_id`, `tenant_id`, `amount_cents`, `paid_at`
- An invoice may have zero, one, or many payments.
