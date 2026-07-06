// Package reports builds tenant-scoped revenue reporting on top of the store. It
// owns both the data access for reporting (combining invoices with the payments
// recorded against them) and the service-level rollups the handlers consume.
package reports

import (
	"sort"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// Service exposes tenant revenue reporting to the handlers.
type Service struct {
	db *store.DB
}

// NewService wires a reports service to db.
func NewService(db *store.DB) *Service {
	return &Service{db: db}
}

// TenantSummary is the headline view of a tenant's revenue.
type TenantSummary struct {
	TenantID   string            `json:"tenant_id"`
	Rows       []model.ReportRow `json:"rows"`
	TotalCents int               `json:"total_cents"`
	PaidCents  int               `json:"paid_cents"`
	DueCents   int               `json:"due_cents"`
}

// TenantReport returns every report row for the tenant plus the rolled-up totals.
func (s *Service) TenantReport(tenantID string) TenantSummary {
	rows := s.TenantRevenue(tenantID)
	var total, paid, due int
	for _, row := range rows {
		total += row.TotalCents
		paid += row.PaidCents
		due += row.DueCents
	}
	return TenantSummary{
		TenantID:   tenantID,
		Rows:       rows,
		TotalCents: total,
		PaidCents:  paid,
		DueCents:   due,
	}
}

// TenantRevenue returns one report row per billable invoice owned by tenantID.
// Every invoice the tenant owns is reported, whether or not any payment has been
// recorded yet; an invoice with no payments reports paid_cents = 0 and the full
// amount still due. Cancelled invoices are not revenue and are left out
// entirely. Rows are ordered by issue date and then invoice id.
func (s *Service) TenantRevenue(tenantID string) []model.ReportRow {
	// Scope invoices to the tenant first, so no other tenant's rows can enter the
	// report through the join. Cancelled invoices are dropped here so they never
	// reach the totals.
	invoices := store.Filter(s.db.Table(repository.TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID &&
			store.AsString(row, "status") != "void"
	})

	// Total the payments for this tenant per invoice.
	payments := store.Filter(s.db.Table(repository.TablePayments).All(), func(row store.Row) bool {
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

// StatusRow is the per-status tally of a tenant's invoices.
type StatusRow struct {
	Status     string `json:"status"`
	Count      int    `json:"count"`
	TotalCents int    `json:"total_cents"`
}

// StatusSummary groups a tenant's invoices by status, reporting how many
// invoices have each status and the sum of their totals. Only the tenant's own
// invoices are counted. Rows are ordered by status so the output is stable.
func (s *Service) StatusSummary(tenantID string) []StatusRow {
	invoices := store.Filter(s.db.Table(repository.TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
	groups := store.GroupCountSum(invoices, "status", "total_cents")

	rows := make([]StatusRow, 0, len(groups))
	for _, g := range groups {
		rows = append(rows, StatusRow{Status: g.Key, Count: g.Count, TotalCents: g.Sum})
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].Status < rows[j].Status })
	return rows
}
