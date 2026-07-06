# Reporting rules

The tenant revenue report answers: for this tenant, what was invoiced, what has
been paid, and what is still due.

Rules:

- A tenant only ever sees its own invoices. A report for one tenant must never
  include another tenant's invoices, customers or payments.
- Every invoice the tenant owns appears in the report, including invoices that
  have not been paid yet. An unpaid invoice reports `paid_cents = 0` and its full
  amount as `due_cents`.
- A `void` invoice is cancelled: it is not revenue and is excluded from the
  report entirely. It is neither listed as a row nor counted in the totals,
  regardless of any payments once recorded against it.
- `paid_cents` for an invoice is the sum of all payments recorded against it.
- `due_cents = total_cents - paid_cents`.
- Rows are ordered by `issued_at`, then by invoice `id`.
- The report totals are the sums of the per-row figures.

## Per-status summary

The per-status summary groups one tenant's invoices by status, reporting for each
status the number of that tenant's invoices with that status and the sum of their
totals.

- Only the tenant's own invoices are counted; another tenant's invoices never
  affect any count or total.
- Each status reports the true number of the tenant's invoices with that status,
  however many there are - not just whether at least one exists.
- Only statuses the tenant actually has appear; a status with no invoices for the
  tenant produces no row.
- The summary reconciles with the tenant as a whole: the per-status counts add up
  to the tenant's total number of invoices, and the per-status totals add up to
  the tenant's overall invoice total.
- Rows are ordered by status.
