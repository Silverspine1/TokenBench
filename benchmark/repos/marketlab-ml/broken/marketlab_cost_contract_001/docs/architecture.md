# marketlab-ml architecture

A small, deterministic backtesting pipeline. Stages, in order:

1. **data_loader** — load candles, sort by time, group by symbol, and assemble
   aligned `(feature, label)` rows. Warmup rows and trailing rows without a
   forward point are dropped here.
2. **features** — causal rolling statistics. A feature at row `i` is computed
   from rows strictly before `i` (point-in-time): it never reads the current or
   any later row.
3. **labels** — forward-looking targets over a `horizon`.
4. **split** — chronological train/test partitioning. For interleaved
   multi-asset data the partition is applied per symbol so each symbol's train
   rows precede its own test rows.
5. **costs** — the per-fill cost model: fee, slippage, and spread. Each
   component is proportional to notional and counted once.
6. **portfolio** — equity-curve construction from per-trade net P&L.
7. **reports / metrics** — reconciled summary. Equity metrics and trade-table
   totals share a single net basis so they cannot disagree.
8. **evaluation** — walk-forward evaluation over sequential, non-overlapping
   test windows.

See `data_contracts.md` for field names and `metric_definitions.md` for exact
metric formulas.
