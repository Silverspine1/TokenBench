# Order State Machine

Order status uses the `PaymentStatus` constants.

## States

- `pending`: created at checkout, no successful payment yet.
- `paid`: at least one successful payment covers the invoice, no refunds.
- `failed`: a payment attempt was declined; this does not block later success.
- `partially_refunded`: refunds exist but are less than the paid amount.
- `refunded`: refunds meet or exceed the paid amount.

## Transitions

- Checkout creates an order in `pending`.
- A successful webhook moves a `pending` order to `paid` and updates the invoice
  paid balance.
- A failed webhook leaves a `pending` order eligible for a fresh attempt.
- A refund recomputes status: `partially_refunded` when `0 < refunded < paid`,
  `refunded` when `refunded >= paid`.

## Idempotency and reconciliation

- A repeated event id is treated as a duplicate and changes nothing.
- A distinct event id carrying a payment reference already fully applied to an
  already-paid order does not double-pay; balances are reconciled by reference.
