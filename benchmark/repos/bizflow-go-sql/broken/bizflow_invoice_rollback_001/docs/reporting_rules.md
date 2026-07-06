# Reporting rules

The tenant revenue report answers: for this tenant, what was invoiced, what has
been paid, and what is still due.

Rules:

- A tenant only ever sees its own invoices. A report for one tenant must never
  include another tenant's invoices, customers or payments.
- Every invoice the tenant owns appears in the report, including invoices that
  have not been paid yet. An unpaid invoice reports `paid_cents = 0` and its full
  amount as `due_cents`.
- `paid_cents` for an invoice is the sum of all payments recorded against it.
- `due_cents = total_cents - paid_cents`.
- Rows are ordered by `issued_at`, then by invoice `id`.
- The report totals are the sums of the per-row figures.
