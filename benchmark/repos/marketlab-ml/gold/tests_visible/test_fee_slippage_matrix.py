"""High-volume net-P&L cost matrix.

This sweep exercises ``net_pnl`` across a deterministic grid of
(gross, notional, fee_rate, slippage_rate) inputs and prints one fully labelled
line per case (case index, the four inputs, the expected net P&L, the value the
implementation returned, the signed error, and PASS/FAIL). The expected value
follows the documented cost model exactly:

    net = gross - notional*fee_rate - notional*slippage_rate

The grid is fixed and offline, so the printed output is byte-for-byte
deterministic for a given implementation. The aggregating assertion at the end
holds only when every case matches the documented model.
"""

from marketlab.backtest import net_pnl

# Fixed, deterministic grid. 7 * 6 * 5 * 3 = 630 cases.
GROSSES = [0.0, 12.5, 50.0, 100.0, 250.5, 1000.0, 4321.75]
NOTIONALS = [500.0, 1000.0, 2000.0, 5000.0, 12500.0, 100000.0]
FEE_RATES = [0.0001, 0.0005, 0.001, 0.0025, 0.01]
SLIPPAGE_RATES = [0.0002, 0.0005, 0.005]


def _cases():
    idx = 0
    for g in GROSSES:
        for n in NOTIONALS:
            for fr in FEE_RATES:
                for sr in SLIPPAGE_RATES:
                    yield idx, g, n, fr, sr
                    idx += 1


def test_net_pnl_cost_matrix():
    failures = 0
    total = 0
    for idx, g, n, fr, sr in _cases():
        total += 1
        expected = g - n * fr - n * sr
        actual = net_pnl(g, n, fr, sr)
        err = actual - expected
        ok = abs(err) < 1e-9
        if not ok:
            failures += 1
        print(
            f"case {idx:04d} | gross={g:12.4f} notional={n:12.2f} "
            f"fee_rate={fr:.6f} slippage_rate={sr:.6f} | "
            f"expected_net={expected:16.6f} actual_net={actual:16.6f} "
            f"error={err:16.6f} | {'PASS' if ok else 'FAIL'}"
        )
    print(f"summary | total={total} failures={failures}")
    assert failures == 0, f"{failures} of {total} net_pnl cases mismatch the cost model"
