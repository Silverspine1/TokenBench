"""Generate a reconciled backtest report and print it as JSON.

Convenience wrapper over :func:`marketlab.reports.build_report` using the
default config and a small synthetic trade list.
"""

from __future__ import annotations

import json

from marketlab.config import Config
from marketlab.reports import build_report


def main() -> int:
    cfg = Config()
    trades = [
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": 25.0},
        {"symbol": "AAA", "notional": 1000.0, "gross_pnl": -10.0},
        {"symbol": "BBB", "notional": 2000.0, "gross_pnl": 40.0},
    ]
    report = build_report(trades, cfg.rates(), cfg.initial_equity)
    print(json.dumps({k: v for k, v in report.items() if k != "equity_curve"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
