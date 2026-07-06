package service

import (
	"errors"
	"fmt"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// ErrUnknownHold is returned when a hold id does not exist.
var ErrUnknownHold = errors.New("holds: unknown hold")

// HoldService places and releases temporary stock reservations (holds). A hold
// ties up units of a product without creating an invoice; while it is live the
// units it holds are not available to anyone else. Placing and releasing happen
// inside a single transaction so a hold is all-or-nothing: a placement that
// cannot reserve its units leaves stock and the hold table untouched.
type HoldService struct {
	db        *store.DB
	holds     *repository.HoldRepo
	products  *repository.ProductRepo
	inventory *InventoryService
	seq       int
}

// NewHoldService wires a hold service to db.
func NewHoldService(db *store.DB) *HoldService {
	return &HoldService{
		db:        db,
		holds:     repository.NewHoldRepo(db),
		products:  repository.NewProductRepo(db),
		inventory: NewInventoryService(db),
	}
}

func (s *HoldService) nextID() string {
	s.seq++
	return fmt.Sprintf("hold-%04d", s.seq)
}

// adjustReserved moves the reserved count of a product by delta (which may be
// negative). It is the single place hold logic touches stock, so reserving and
// freeing always go through the same path.
func (s *HoldService) adjustReserved(tenantID, sku string, delta int) {
	s.db.Table(repository.TableProducts).Update(
		func(row store.Row) bool {
			return store.AsString(row, "tenant_id") == tenantID && store.AsString(row, "sku") == sku
		},
		func(row store.Row) store.Row {
			row["reserved"] = store.AsInt(row, "reserved") + delta
			return row
		},
	)
}

// Place creates a hold for qty units of sku and reserves that stock. It fails,
// changing nothing, when the product is unknown or there is not enough available
// stock. On success the stored hold is returned. A hold placed this way never
// expires on its own.
func (s *HoldService) Place(tenantID, sku string, qty int, at string) (model.Hold, error) {
	return s.PlaceUntil(tenantID, sku, qty, at, "")
}

// PlaceUntil is Place with an expiry date. An empty expiresAt means the hold
// never expires. The expiry is just recorded here; ExpireBefore is what acts on
// it.
func (s *HoldService) PlaceUntil(tenantID, sku string, qty int, at, expiresAt string) (model.Hold, error) {
	p, ok := s.products.Get(tenantID, sku)
	if !ok {
		return model.Hold{}, ErrUnknownProduct
	}
	if qty <= 0 || qty > p.Available() {
		return model.Hold{}, ErrInsufficientStock
	}

	seqBefore := s.seq
	h := model.Hold{
		ID:        s.nextID(),
		TenantID:  tenantID,
		SKU:       sku,
		Quantity:  qty,
		CreatedAt: at,
		ExpiresAt: expiresAt,
	}

	tx := s.db.Begin()
	s.holds.Insert(h)
	s.adjustReserved(tenantID, sku, qty)
	if err := tx.Commit(); err != nil {
		s.seq = seqBefore
		return model.Hold{}, err
	}
	return h, nil
}

// Release frees a hold's reserved stock and removes the hold. Releasing an
// unknown hold reports ErrUnknownHold and changes nothing.
func (s *HoldService) Release(holdID string) error {
	return s.consume(holdID, 0, false)
}

// Fulfill turns some or all of a hold into a real sale: it draws qty units down
// from on-hand stock and frees those units from the reservation. When qty is at
// least the hold's remaining quantity the whole hold is fulfilled and removed;
// otherwise the hold shrinks by qty and stays live for the rest. A qty of zero
// or less, or fulfilling an unknown hold, reports ErrUnknownHold or changes
// nothing.
func (s *HoldService) Fulfill(holdID string, qty int) error {
	if qty <= 0 {
		return nil
	}
	return s.consume(holdID, qty, true)
}

// ExpireBefore releases every hold whose expiry date is on or before now,
// giving the held stock back. Holds with no expiry, or an expiry later than now,
// are left untouched. It returns the number of holds released.
func (s *HoldService) ExpireBefore(now string) int {
	released := 0
	for _, h := range s.holds.All() {
		if h.ExpiresAt != "" && h.ExpiresAt <= now {
			if s.consume(h.ID, 0, false) == nil {
				released++
			}
		}
	}
	return released
}

// consume frees `units` of a hold's reserved stock. When units == 0 the whole
// hold is released. The optional fulfil flag also draws the consumed units down
// from on-hand stock (used when a hold is turned into a real sale). Everything
// happens inside a single transaction so the hold table and stock never drift
// apart.
//
// Stage 1 only releases whole holds (units == 0, fulfil == false); the extra
// parameters give later behaviour a single shared path to build on.
func (s *HoldService) consume(holdID string, units int, fulfil bool) error {
	h, ok := s.holds.Get(holdID)
	if !ok {
		return ErrUnknownHold
	}
	if units <= 0 || units >= h.Quantity {
		units = h.Quantity
	}

	tx := s.db.Begin()
	// Free the reserved units; this hold no longer ties them up.
	s.adjustReserved(h.TenantID, h.SKU, -units)
	if fulfil {
		// A fulfilled hold also leaves the warehouse, so on-hand drops too.
		s.db.Table(repository.TableProducts).Update(
			func(row store.Row) bool {
				return store.AsString(row, "tenant_id") == h.TenantID && store.AsString(row, "sku") == h.SKU
			},
			func(row store.Row) store.Row {
				row["on_hand"] = store.AsInt(row, "on_hand") - units
				return row
			},
		)
	}
	if units >= h.Quantity {
		s.holds.Delete(holdID)
	} else {
		s.holds.SetQuantity(holdID, h.Quantity-units)
	}
	return tx.Commit()
}

// List returns every live hold owned by the tenant.
func (s *HoldService) List(tenantID string) []model.Hold {
	return s.holds.ListByTenant(tenantID)
}
