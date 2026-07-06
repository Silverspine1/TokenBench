# Statistics rules

`summarize` reports `count`, `sum`, `mean`, `min` and `max` over a column of
numbers. An empty column reports zero for every figure.

`min` and `max` are the least and greatest values actually present, taken from the
data itself rather than from any fixed starting figure, so they are correct even
when every value is negative (`-3, -2, -1` has min `-3` and max `-1`) and when a
single value is its own min and max. When every value is identical, both `min` and
`max` are that value. `mean` is the true average -- the sum divided as a real
quantity, so `1, 2` has mean `1.5`, never a whole-number quotient. The figures use
each reading exactly as given, including its sign; readings are never reduced to
their magnitudes.

`rollingMean(values, window)` returns the moving average over a sliding window.
There is one output per full window, so the result has `values.size() - window + 1`
entries and `result[i]` is the mean of `values[i .. i + window - 1]`. A window of
zero, or a window larger than the input, yields an empty result. A window equal to
the number of values yields a single output equal to the mean of every value.

`windowMeans(records, index, window)` takes the moving average straight from a
file column. It reads the numeric readings out of that column -- skipping any rows
whose cell is not a number -- and then takes the rolling mean over the readings
that remain, in their original order. The non-numeric rows are simply absent from
the series; they do not split it or shift it. So a column whose numeric readings
are 10, 20, 30 (with other, non-numeric rows interleaved) has window-2 means of 15
and 25, and a window of 3 gives the single mean 20.

`parseDouble` accepts an optional sign, a decimal point and a scientific exponent
(`1.5e3`, `-2E-2`, `+3.5`). Leading and trailing spaces are ignored. A field that
is not entirely a single number is treated as having no numeric value.

Only ordinary decimal numbers count as readings. A field is made up solely of the
decimal-number characters: digits, an optional sign, a decimal point and a
decimal exponent (`e`/`E`). Anything outside that set is not a reading. In
particular the words `inf`/`nan` (in any case) and hexadecimal floats such as
`0x1p4` are rejected and yield no value, even though a permissive
string-to-double conversion would otherwise accept them, and a reading must
denote a finite quantity.
