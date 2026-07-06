"""Backtester cost model and equity-curve metrics."""


def net_pnl(gross_pnl: float, notional: float, fee_rate: float, slippage_rate: float) -> float:
    """Net P&L after trading fees and slippage on a fill.

    fee      = notional * fee_rate
    slippage = notional * slippage_rate
    """
    fee = notional * fee_rate
    slippage = notional * slippage_rate
    # Apply transaction costs for the executed fill.
    return gross_pnl - fee - slippage


def compute_metrics(equity_curve: list[float]) -> dict:
    """Summary metrics for an equity curve.

    Returns:
        final_equity : last point of the curve
        total_return : (final - initial) / initial
        num_periods  : number of step transitions (len - 1)
        max_drawdown : largest peak-to-trough fractional decline (>= 0)
    """
    if not equity_curve:
        return {
            "final_equity": 0.0,
            "total_return": 0.0,
            "num_periods": 0,
            "max_drawdown": 0.0,
        }

    initial = equity_curve[0]
    final = equity_curve[-1]
    total_return = (final - initial) / initial if initial else 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    return {
        "final_equity": final,
        "total_return": total_return,
        "num_periods": len(equity_curve) - 1,
        "max_drawdown": max_drawdown,
    }
