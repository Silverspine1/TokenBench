# Formatting rules

`formatFixed(value, precision)` prints a number with exactly `precision` digits
after the decimal point. Rounding is half away from zero, and a value that rounds
to zero is printed as `0` (never `-0`).

`formatColumns(rows)` lays out rows of string cells as a left-aligned table. Each
column is padded to the width of its widest cell and columns are separated by two
spaces. Every row ends with a newline.
