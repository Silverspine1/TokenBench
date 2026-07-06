# Webhook Contracts

Each provider exposes a mock gateway with a shared secret. A signature is the
hex `hash_hmac('sha256', $rawBody, SECRET)`. Fixtures can produce valid
signatures via each gateway's static `sign($rawBody)` helper.

## Signature headers

- Stripe: `Stripe-Signature`
- PayFast: `X-PayFast-Signature`

## Normalized event

`GatewayEventNormalizer::normalize($provider, $payload)` returns exactly:

```
['provider', 'eventId', 'paymentReference', 'status', 'amountCents', 'currency']
```

- `status` passes through `PaymentStatus::normalize`.
- `amountCents` is always integer cents.
- `currency` is an uppercase three-letter code.

## Supported payload shapes

### Stripe new

```
{ "id": "...", "data": { "object": { "id": "...", "amount": 1234, "currency": "usd", "status": "succeeded" } } }
```

The top-level `id` is the event id; `data.object.id` is the payment reference;
`amount` is already in cents.

### Stripe old

```
{ "event_id": "...", "payment_ref": "...", "amount_cents": 1234, "currency": "USD", "status": "Paid" }
```

### PayFast new

```
{ "m_payment_id": "...", "pf_payment_id": "...", "amount_gross": "12.34", "currency_code": "ZAR", "payment_status": "COMPLETE" }
```

`m_payment_id` is the event id; `pf_payment_id` is the payment reference;
`amount_gross` is a decimal string converted to cents.

### PayFast old

```
{ "payment_id": "...", "reference": "...", "amount": "12.34", "currency": "ZAR", "status": "completed" }
```
