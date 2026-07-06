# Currency rules

* All money is stored and computed in **integer cents**. Never use floating
  dollars in totals.
* An invoice's `amountCents` is its gross amount.
* `paid` is the sum of `payments` (cents); `credited` is the sum of `credits`
  (cents).
* `outstanding = max(0, gross - paid - credited)`. Overpayment (paid + credited
  greater than gross) clamps outstanding to `0`; it never goes negative.
* Status labels (`paid`, `open`, `overdue`, ...) are preserved exactly as they
  appear on the invoice; summarizing never renames or merges them.
