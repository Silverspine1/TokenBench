# Money Rules

All monetary values are integer cents internally. Floating point is never used
for money arithmetic.

## Parsing decimal strings

`Money::fromDecimalString($amount, $currency)` parses via string handling:

- `"12.34"` becomes `1234`.
- `"12"` becomes `1200`.
- `"12.5"` becomes `1250`.
- A leading `-` produces negative cents, for example `"-3.07"` becomes `-307`.

## Formatting

`Money::toDecimalString()` renders cents back to a two-decimal string, for
example `1205` becomes `"12.05"`.

## Arithmetic

`add` and `subtract` require matching currencies and throw on mismatch. Equality
compares both cents and currency.

## Invariants

For each report row, `(paidCents - refundedCents) + dueCents == totalCents`.
Invoice balances reconcile with reports exactly in integer cents.
