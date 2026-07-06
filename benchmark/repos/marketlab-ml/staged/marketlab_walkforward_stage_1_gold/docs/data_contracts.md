# Data contracts

## Candle (input row)

| field  | type  | notes                               |
|--------|-------|-------------------------------------|
| t      | int   | period index, ascending per symbol  |
| symbol | str   | asset identifier                    |
| close  | float | closing price                       |

Candle series may have **gaps** (missing `t` values). Alignment is by row
position in arrival order, not by arithmetic on `t`.

## Dataset row (output of build_dataset)

| field   | type  | notes                                              |
|---------|-------|----------------------------------------------------|
| t       | int   | time of the row                                    |
| feature | float | rolling statistic over the prior `window` rows     |
| label   | int   | 1 if price rose over the next `horizon` rows else 0|

The first `window` warmup rows and the final `horizon` rows are dropped.

## Trade

| field    | type  | notes                          |
|----------|-------|--------------------------------|
| symbol   | str   | asset                          |
| notional | float | absolute traded value          |
| gross_pnl| float | profit before transaction cost |

## Report

Keys: `trades`, `gross_pnl`, `net_pnl`, `cost_breakdown` (`fee`, `slippage`,
`spread`, `total`), `equity_curve`, `equity_delta`, `metrics`.
