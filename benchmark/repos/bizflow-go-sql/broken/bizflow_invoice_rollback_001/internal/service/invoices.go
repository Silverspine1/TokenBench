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
// no stock is reserved. On success the stored invoice is returned.
func (s *InvoiceService) Create(tenantID, customer, issuedAt string, lines []model.InvoiceLine) (model.Invoice, error) {
	if len(lines) == 0 {
		return model.Invoice{}, ErrEmptyInvoice
	}

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
			return model.Invoice{}, err
		}
	}
	if err := tx.Commit(); err != nil {
		return model.Invoice{}, err
	}
	return inv, nil
}
