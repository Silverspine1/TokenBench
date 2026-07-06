# Inventory rules

- A reservation may never take availability below zero. A line that asks for more
  than `on_hand - reserved` units is rejected.
- Creating an invoice reserves stock for every line. Invoice creation and the
  reservations it makes are one unit of work: if any line cannot be reserved, the
  whole invoice is abandoned and no stock is reserved and no invoice is stored.
- Unknown SKUs are rejected.
