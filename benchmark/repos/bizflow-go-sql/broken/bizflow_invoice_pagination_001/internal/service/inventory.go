// Package service holds the business logic that sits between the HTTP handlers
// and the repositories.
package service

import (
	"errors"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

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
