# Inventory rules

- A reservation may never take availability below zero. A line that asks for more
  than `on_hand - reserved` units is rejected.
- Creating an invoice reserves stock for every line. Invoice creation and the
  reservations it makes are one unit of work: if any line cannot be reserved, the
  whole invoice is abandoned and no stock is reserved and no invoice is stored.
- The combined demand for a product across all lines of one invoice must fit; two
  lines that each fit on their own but together exceed the stock are rejected as a
  whole.
- An abandoned creation leaves no trace at all, including the invoice numbering:
  an attempt that does not produce an invoice does not advance the invoice
  numbers, so the next successful creation takes the number the failed attempt
  would have used and there is no gap in the sequence.
- Unknown SKUs are rejected.
