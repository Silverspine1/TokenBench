# Equity-curve metrics

`marketlab.backtest.compute_metrics` summarises an equity curve.

| Metric         | Definition                                             |
|----------------|--------------------------------------------------------|
| `final_equity` | Last point of the curve.                               |
| `total_return` | `(final - initial) / initial`.                         |
| `num_periods`  | Number of step transitions, i.e. `len(curve) - 1`.     |
| `max_drawdown` | Largest peak-to-trough fractional decline, `>= 0`.     |

`max_drawdown` walks the curve tracking the running peak and records the deepest
fractional decline from that peak.
