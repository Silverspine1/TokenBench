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
