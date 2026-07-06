# Payment Flow

The portal coordinates checkout, gateway webhooks, refunds, and reporting.

## Checkout

`CheckoutService::checkout(string $sessionId, Cart $cart): Order`

- A cart carries a currency and a list of line items. Each item has a `sku`,
  a `quantity`, and a `unitCents` unit price expressed in integer cents.
- The cart fingerprint is a deterministic SHA-256 over the sorted items and the
  currency. Two carts with identical contents share a fingerprint regardless of
  item ordering.
- When a session already has a pending order whose fingerprint matches the
  incoming cart, that order (and its single invoice) is reused.
- When the fingerprint differs, a new order and invoice pair is created.
- Exactly one invoice exists per order.

## Webhooks

Gateway callbacks arrive as a raw JSON body plus provider headers. The flow is:

1. Verify the provider signature. Invalid signatures are rejected before any
   state change.
2. Normalize the payload into a provider-neutral event.
3. If the event id was already processed, report it as a duplicate without
   mutating state.
4. Otherwise record the payment, update the invoice and order, and mark the
   event id as processed.

## Refunds

`RefundService::refund(string $paymentId, int $amountCents): Refund` records a
refund against a payment, updates the related invoice, and recomputes the order
status. A refund that would push total refunded above the paid amount is
rejected.

## Reporting

`PaymentReportService::report()` emits one row per order with totals, paid,
due, and status, all in integer cents.
