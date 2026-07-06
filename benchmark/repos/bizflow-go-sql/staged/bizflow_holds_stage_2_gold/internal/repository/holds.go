package repository

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// HoldRepo reads and writes hold rows. A hold is a temporary stock reservation.
type HoldRepo struct {
	db *store.DB
}

// NewHoldRepo returns a repository bound to db, ensuring the table exists.
func NewHoldRepo(db *store.DB) *HoldRepo {
	db.CreateTable(TableHolds, "id", "tenant_id", "sku", "quantity", "created_at", "expires_at")
	return &HoldRepo{db: db}
}

// holdRow flattens a hold into a storable row.
func holdRow(h model.Hold) store.Row {
	return store.Row{
		"id":         h.ID,
		"tenant_id":  h.TenantID,
		"sku":        h.SKU,
		"quantity":   h.Quantity,
		"created_at": h.CreatedAt,
		"expires_at": h.ExpiresAt,
	}
}

func holdFromRow(row store.Row) model.Hold {
	return model.Hold{
		ID:        store.AsString(row, "id"),
		TenantID:  store.AsString(row, "tenant_id"),
		SKU:       store.AsString(row, "sku"),
		Quantity:  store.AsInt(row, "quantity"),
		CreatedAt: store.AsString(row, "created_at"),
		ExpiresAt: store.AsString(row, "expires_at"),
	}
}

// Insert stores one hold.
func (r *HoldRepo) Insert(h model.Hold) {
	r.db.Table(TableHolds).Insert(holdRow(h))
}

// Get returns the hold with the given id and whether it was found.
func (r *HoldRepo) Get(id string) (model.Hold, bool) {
	rows := store.Filter(r.db.Table(TableHolds).All(), func(row store.Row) bool {
		return store.AsString(row, "id") == id
	})
	if len(rows) == 0 {
		return model.Hold{}, false
	}
	return holdFromRow(rows[0]), true
}

// ListByTenant returns every live hold owned by tenantID, in insertion order.
func (r *HoldRepo) ListByTenant(tenantID string) []model.Hold {
	rows := store.Filter(r.db.Table(TableHolds).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
	out := make([]model.Hold, 0, len(rows))
	for _, row := range rows {
		out = append(out, holdFromRow(row))
	}
	return out
}

// All returns every live hold, in insertion order.
func (r *HoldRepo) All() []model.Hold {
	rows := r.db.Table(TableHolds).All()
	out := make([]model.Hold, 0, len(rows))
	for _, row := range rows {
		out = append(out, holdFromRow(row))
	}
	return out
}

// SetQuantity rewrites the quantity of the hold with the given id.
func (r *HoldRepo) SetQuantity(id string, quantity int) {
	r.db.Table(TableHolds).Update(
		func(row store.Row) bool { return store.AsString(row, "id") == id },
		func(row store.Row) store.Row {
			row["quantity"] = quantity
			return row
		},
	)
}

// Delete removes the hold with the given id.
func (r *HoldRepo) Delete(id string) {
	r.db.Table(TableHolds).Delete(func(row store.Row) bool {
		return store.AsString(row, "id") == id
	})
}
