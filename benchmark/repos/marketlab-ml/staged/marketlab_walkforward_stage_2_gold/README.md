# marketlab-ml

A small research toolkit for backtesting trading signals on OHLCV candle data.

## Layout

```
marketlab/        core library (features, labels, splitting, backtest metrics)
configs/          default run configuration
docs/             modelling assumptions and metric definitions
scripts/          small entry points for local experiments
fixtures/         tiny sample data used by examples and local runs
tests_visible/    fast smoke tests you can run while developing
```

## Running the smoke tests

```
pytest -q tests_visible
```

## Modules

- `marketlab.features` — rolling features built only from prior bars.
- `marketlab.labels` — forward up/down labels over a fixed horizon.
- `marketlab.split` — chronological train/test partitioning.
- `marketlab.backtest` — cost model and equity-curve metrics.
