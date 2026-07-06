# Backtesting assumptions

These are the modelling conventions the library relies on. They keep results
reproducible and comparable across experiments.

## Causality

A signal evaluated at bar `i` may only use information available up to and
including the prior bar. Rolling features therefore aggregate the rows that come
before `i`; the current bar is not part of its own feature value.

## Labels

A forward label at bar `i` compares the price `horizon` periods ahead against
the price at `i`. The trailing rows that have no point `horizon` steps ahead are
left unlabelled (`None`).

## Train / test partitioning

Splitting is chronological. The earliest rows form the training set and the most
recent rows form the test set, preserving time order.

## Costs

Each fill is charged a fee on its notional plus a modelled slippage component.
Both are applied once per fill.
