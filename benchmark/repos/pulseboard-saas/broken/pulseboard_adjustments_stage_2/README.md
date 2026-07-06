# pulseboard-saas

Billing and reporting helpers for the Pulseboard invoice dashboard.

## Layout

```
src/              invoice domain logic (contract, filtering, pagination, export, summary)
docs/             API contracts and filtering rules
fixtures/         small sample invoices used by examples and local runs
scripts/          small entry points for local experiments
tests_visible/    fast smoke tests you can run while developing
```

## Running the smoke tests

```
node tests_visible/run_visible_tests.js
```

## Modules

- `src/contract.js` — normalize the API invoice shape into the internal shape.
- `src/datefilter.js` — filter invoices by their local due date.
- `src/pagination.js` — page through an invoice list.
- `src/export.js` — render a filtered invoice set to CSV.
- `src/summary.js` — counts and totals per invoice status.
