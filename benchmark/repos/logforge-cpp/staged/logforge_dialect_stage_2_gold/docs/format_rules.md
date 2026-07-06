# Formatting rules

`formatFixed(value, precision)` prints a number with exactly `precision` digits
after the decimal point. Rounding is half away from zero, and a value that rounds
to zero is printed as `0` (never `-0`).

Rounding carries the way ordinary arithmetic does, even across the decimal point
and across several places: `9.999` to two places is `10.00`, `-9.999` to two
places is `-10.00`, and `99.999` to two places is `100.00`. The no-negative-zero
rule applies to results that reach zero only after rounding, so a tiny negative
input such as `-0.004` prints as `0.00`, not `-0.00`.

`formatColumns(rows)` lays out rows of string cells as a left-aligned table. Each
column is padded to the width of its widest cell and columns are separated by two
spaces. Every row ends with a newline.
