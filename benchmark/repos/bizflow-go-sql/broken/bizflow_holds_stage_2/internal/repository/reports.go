package repository

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// ReportRepo builds tenant-scoped revenue reports by combining invoices with the
// payments recorded against them.
type ReportRepo struct {
	db *store.DB
}

// NewReportRepo returns a report repository bound to db.
func NewReportRepo(db *store.DB) *ReportRepo {
	return &ReportRepo{db: db}
}

// TenantRevenue returns one report row per billable invoice owned by tenantID.
// Every invoice the tenant owns is reported, whether or not any payment has been
// recorded yet; an invoice with no payments reports paid_cents = 0 and the full
// amount still due. Cancelled invoices are not revenue and are left out
// entirely. Rows are ordered by issue date and then invoice id.
func (r *ReportRepo) TenantRevenue(tenantID string) []model.ReportRow {
	// Scope invoices to the tenant first, so no other tenant's rows can enter the
	// report through the join. Cancelled invoices are dropped here so they never
	// reach the totals.
	invoices := store.Filter(r.db.Table(TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID &&
			store.AsString(row, "status") != "void"
	})

	// Total the payments for this tenant per invoice.
	payments := store.Filter(r.db.Table(TablePayments).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
	paid := store.GroupSum(payments, "invoice_id", "amount_cents")
	for _, p := range paid {
		p["paid_cents"] = store.AsInt(p, "amount_cents")
	}

	// Left join keeps invoices that have no payments yet.
	joined := store.LeftJoin(invoices, paid, "id", "invoice_id")
	ordered := store.OrderByString(joined, "issued_at", "id")

	rows := make([]model.ReportRow, 0, len(ordered))
	for _, row := range ordered {
		total := store.AsInt(row, "total_cents")
		paidCents := store.AsInt(row, "paid_cents")
		rows = append(rows, model.ReportRow{
			InvoiceID:  store.AsString(row, "id"),
			Customer:   store.AsString(row, "customer"),
			Status:     store.AsString(row, "status"),
			TotalCents: total,
			PaidCents:  paidCents,
			DueCents:   total - paidCents,
		})
	}
	return rows
}

// TenantTotals sums the report into headline figures for the tenant.
func (r *ReportRepo) TenantTotals(tenantID string) (totalCents, paidCents, dueCents int) {
	for _, row := range r.TenantRevenue(tenantID) {
		totalCents += row.TotalCents
		paidCents += row.PaidCents
		dueCents += row.DueCents
	}
	return totalCents, paidCents, dueCents
}
