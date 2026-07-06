# Metric definitions

All monetary figures are in account currency. Returns are additive per period.

## Cost components (per fill)

    fee      = |notional| * fee_rate
    slippage = |notional| * slippage_rate
    spread   = |notional| * spread_rate
    total    = fee + slippage + spread

The total is counted exactly once per fill.

## P&L reconciliation

    net_pnl      = gross_pnl - total_cost
    equity_delta = final_equity - initial_equity
    equity_delta = net_pnl                     (must hold for any report)

The trade-table net total and the equity-curve delta are the same number.

## Equity-curve metrics

    final_equity : last point of the curve
    total_return : (final - initial) / initial
    max_drawdown : largest peak-to-trough fractional decline, >= 0

## Walk-forward aggregate

    mean_return  : mean of per-window mean returns
    max_drawdown : worst (maximum) per-window drawdown
    win_rate     : mean of per-window win rates
