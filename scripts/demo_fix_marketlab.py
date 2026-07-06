"""Demo fix for the local-command runner. Runs with cwd == workspace.

Rewrites the broken net_pnl so the fee is charged once and slippage applies.
"""

import pathlib

p = pathlib.Path("marketlab/backtest.py")
p.write_text(p.read_text().replace("gross_pnl - fee - fee", "gross_pnl - fee - slippage"))
print("fixed marketlab/backtest.py")
