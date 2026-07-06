# API contracts

## Invoice shapes

The billing API returns invoices in snake_case with monetary amounts in cents:

```json
{ "id": 7, "status": "paid", "amount_cents": 1299 }
```

The UI and export layers work in camelCase:

```json
{ "id": 7, "status": "paid", "amountCents": 1299 }
```

`src/contract.js` is the single boundary that translates the API shape into the
internal shape. Every field the UI consumes must be present after normalization.

## Status values

`status` is one of `paid`, `open`, or `void`. Reporting groups invoices by this
field.
