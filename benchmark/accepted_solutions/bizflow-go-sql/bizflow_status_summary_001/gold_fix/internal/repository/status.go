package repository

import (
	"sort"

	"bizflow/internal/store"
)

// StatusRow is the per-status tally of a tenant's invoices.
type StatusRow struct {
	Status     string `json:"status"`
	Count      int    `json:"count"`
	TotalCents int    `json:"total_cents"`
}

// StatusSummary groups a tenant's invoices by status, reporting how many
// invoices have each status and the sum of their totals. Only the tenant's own
// invoices are counted. Rows are ordered by status so the output is stable.
func (r *ReportRepo) StatusSummary(tenantID string) []StatusRow {
	invoices := store.Filter(r.db.Table(TableInvoices).All(), func(row store.Row) bool {
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
