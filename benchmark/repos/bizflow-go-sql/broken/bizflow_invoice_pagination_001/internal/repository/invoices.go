// Package repository maps the domain model onto the in-memory store. It owns the
// table layout and every query the services rely on.
package repository

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// Table names used across the repositories.
const (
	TableInvoices = "invoices"
	TablePayments = "payments"
	TableProducts = "products"
)

// InvoiceRepo reads and writes invoice rows.
type InvoiceRepo struct {
	db *store.DB
}

// NewInvoiceRepo returns a repository bound to db, ensuring the table exists.
func NewInvoiceRepo(db *store.DB) *InvoiceRepo {
	db.CreateTable(TableInvoices, "id", "tenant_id", "customer", "status", "issued_at", "total_cents")
	return &InvoiceRepo{db: db}
}

// invoiceRow flattens an invoice into a storable row, precomputing its total.
func invoiceRow(inv model.Invoice) store.Row {
	return store.Row{
		"id":          inv.ID,
		"tenant_id":   inv.TenantID,
		"customer":    inv.Customer,
		"status":      inv.Status,
		"issued_at":   inv.IssuedAt,
		"total_cents": inv.Total(),
	}
}

// Insert stores one invoice.
func (r *InvoiceRepo) Insert(inv model.Invoice) {
	r.db.Table(TableInvoices).Insert(invoiceRow(inv))
}

// ListByTenant returns every invoice owned by tenantID, in insertion order.
func (r *InvoiceRepo) ListByTenant(tenantID string) []store.Row {
	return store.Filter(r.db.Table(TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
}

// PageByTenant returns one page of the tenant's invoices. The tenant's invoices
// are ordered by issue date and then id, and the page is the slice of that
// ordered list starting at cursor and holding at most limit rows. Paging from
// cursor 0 and following the returned NextCursor visits every invoice exactly
// once, in order, with no row skipped or repeated at a page boundary.
func (r *InvoiceRepo) PageByTenant(tenantID string, cursor, limit int) store.Page {
	return store.Paginate(r.ListByTenant(tenantID), cursor, limit)
}
