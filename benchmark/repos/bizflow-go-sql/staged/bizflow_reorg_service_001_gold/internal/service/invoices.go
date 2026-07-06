// Package service holds the business logic that sits between the HTTP handlers
// and the repositories: invoice creation and the inventory/stock logic it
// depends on.
package service

import (
	"errors"
	"fmt"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// ErrEmptyInvoice is returned when an invoice has no lines.
var ErrEmptyInvoice = errors.New("invoice: must have at least one line")

// ErrInsufficientStock is returned when a reservation asks for more units than
// are available.
var ErrInsufficientStock = errors.New("inventory: insufficient stock")

// ErrUnknownProduct is returned when a SKU is not stocked for the tenant.
var ErrUnknownProduct = errors.New("inventory: unknown product")

// InventoryService manages stock levels and reservations.
type InventoryService struct {
	db       *store.DB
	products *repository.ProductRepo
}

// NewInventoryService wires an inventory service to db.
func NewInventoryService(db *store.DB) *InventoryService {
	return &InventoryService{db: db, products: repository.NewProductRepo(db)}
}

// Available reports how many units of sku the tenant can still reserve.
func (s *InventoryService) Available(tenantID, sku string) (int, error) {
	p, ok := s.products.Get(tenantID, sku)
	if !ok {
		return 0, ErrUnknownProduct
	}
	return p.Available(), nil
}

// Reserve increases the reserved count for one product line. It fails, changing
// nothing, when the product is unknown or there is not enough available stock.
func (s *InventoryService) Reserve(tenantID, sku string, qty int) error {
	p, ok := s.products.Get(tenantID, sku)
	if !ok {
		return ErrUnknownProduct
	}
	if qty > p.Available() {
		return ErrInsufficientStock
	}
	s.db.Table(repository.TableProducts).Update(
		func(row store.Row) bool {
			return store.AsString(row, "tenant_id") == tenantID && store.AsString(row, "sku") == sku
		},
		func(row store.Row) store.Row {
			row["reserved"] = store.AsInt(row, "reserved") + qty
			return row
		},
	)
	return nil
}

// CheckReservable verifies that the combined demand across lines can be
// satisfied from current availability, without changing any stock.
func (s *InventoryService) CheckReservable(tenantID string, lines []model.InvoiceLine) error {
	want := map[string]int{}
	for _, l := range lines {
		want[l.SKU] += l.Quantity
	}
	for sku, qty := range want {
		p, ok := s.products.Get(tenantID, sku)
		if !ok {
			return ErrUnknownProduct
		}
		if qty > p.Available() {
			return ErrInsufficientStock
		}
	}
	return nil
}

// InvoiceService creates invoices and reserves the stock they consume.
type InvoiceService struct {
	db        *store.DB
	invoices  *repository.InvoiceRepo
	inventory *InventoryService
	seq       int
}

// NewInvoiceService wires an invoice service to db.
func NewInvoiceService(db *store.DB) *InvoiceService {
	return &InvoiceService{
		db:        db,
		invoices:  repository.NewInvoiceRepo(db),
		inventory: NewInventoryService(db),
	}
}

// nextID returns a deterministic, monotonically increasing invoice id.
func (s *InvoiceService) nextID() string {
	s.seq++
	return fmt.Sprintf("inv-%04d", s.seq)
}

// Create records a new invoice for the tenant and reserves the stock for each
// line. Creation and reservation happen inside a single transaction: if any line
// cannot be reserved, the whole operation is undone and no invoice is stored and
// no stock is reserved. A creation that fails leaves no trace at all - including
// the invoice numbering, which is not advanced by an attempt that did not
// produce an invoice, so the next successful creation takes the number the failed
// attempt would have used. On success the stored invoice is returned.
func (s *InvoiceService) Create(tenantID, customer, issuedAt string, lines []model.InvoiceLine) (model.Invoice, error) {
	if len(lines) == 0 {
		return model.Invoice{}, ErrEmptyInvoice
	}

	// Remember the numbering position so a failed attempt can hand the number
	// back; an abandoned creation must leave no gap in the invoice numbers.
	seqBefore := s.seq
	inv := model.Invoice{
		ID:       s.nextID(),
		TenantID: tenantID,
		Customer: customer,
		Status:   "open",
		IssuedAt: issuedAt,
		Lines:    lines,
	}

	tx := s.db.Begin()
	s.invoices.Insert(inv)
	for _, l := range lines {
		if err := s.inventory.Reserve(tenantID, l.SKU, l.Quantity); err != nil {
			tx.Rollback()
			s.seq = seqBefore
			return model.Invoice{}, err
		}
	}
	if err := tx.Commit(); err != nil {
		s.seq = seqBefore
		return model.Invoice{}, err
	}
	return inv, nil
}
