package legacy

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// This barrel re-exposes the tangled internals under their original public
// spellings so existing call sites keep working while everything still lives in
// one package. It maps the terse internal names onto the names the rest of the
// app expects.

// Public error aliases.
var (
	ErrInsufficientStock = E1
	ErrUnknownProduct    = E2
	ErrEmptyInvoice      = E3
)

// InventoryService is the public face of the stock logic.
type InventoryService = Iv

// NewInventoryService wires an inventory service to db.
func NewInventoryService(db *store.DB) *InventoryService { return MkIv(db) }

// InvoiceService is the public face of the invoice-creation logic.
type InvoiceService = Iw

// NewInvoiceService wires an invoice service to db.
func NewInvoiceService(db *store.DB) *InvoiceService { return MkIw(db) }

// ReportService is the public face of the reporting logic.
type ReportService = Rp

// NewReportService wires a report service to db.
func NewReportService(db *store.DB) *ReportService { return MkRp(db) }

// TenantSummary is the public name for the headline revenue view.
type TenantSummary = Ts

// StatusRow is the public name for a per-status tally row.
type StatusRow = Sr

// Available reports how many units of sku the tenant can still reserve.
func (s *Iv) Available(tenantID, sku string) (int, error) { return s.A(tenantID, sku) }

// Reserve increases the reserved count for one product line.
func (s *Iv) Reserve(tenantID, sku string, qty int) error { return s.R(tenantID, sku, qty) }

// CheckReservable verifies combined demand can be satisfied without mutating.
func (s *Iv) CheckReservable(tenantID string, lines []model.InvoiceLine) error {
	return s.C(tenantID, lines)
}

// Create records a new invoice and reserves its stock.
func (s *Iw) Create(tenantID, customer, issuedAt string, lines []model.InvoiceLine) (model.Invoice, error) {
	return s.Mk(tenantID, customer, issuedAt, lines)
}

// TenantReport returns the tenant's revenue rows and rolled-up totals.
func (s *Rp) TenantReport(tenantID string) TenantSummary { return s.T(tenantID) }

// TenantRevenue returns one report row per billable invoice.
func (s *Rp) TenantRevenue(tenantID string) []model.ReportRow { return s.Rv(tenantID) }

// StatusSummary groups the tenant's invoices by status.
func (s *Rp) StatusSummary(tenantID string) []StatusRow { return s.S(tenantID) }
