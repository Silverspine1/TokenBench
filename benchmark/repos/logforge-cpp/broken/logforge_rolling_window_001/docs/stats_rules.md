# Statistics rules

`summarize` reports `count`, `sum`, `mean`, `min` and `max` over a column of
numbers. An empty column reports zero for every figure.

`rollingMean(values, window)` returns the moving average over a sliding window.
There is one output per full window, so the result has `values.size() - window + 1`
entries and `result[i]` is the mean of `values[i .. i + window - 1]`. A window of
zero, or a window larger than the input, yields an empty result.

`parseDouble` accepts an optional sign, a decimal point and a scientific exponent
(`1.5e3`, `-2E-2`). Leading and trailing spaces are ignored. A field that is not
entirely a single number is treated as having no numeric value.
