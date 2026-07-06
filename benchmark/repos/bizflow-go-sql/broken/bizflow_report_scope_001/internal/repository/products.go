package repository

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// ProductRepo reads and writes inventory rows.
type ProductRepo struct {
	db *store.DB
}

// NewProductRepo returns a repository bound to db, ensuring the table exists.
func NewProductRepo(db *store.DB) *ProductRepo {
	db.CreateTable(TableProducts, "tenant_id", "sku", "name", "on_hand", "reserved")
	return &ProductRepo{db: db}
}

// Insert stores one product.
func (r *ProductRepo) Insert(p model.Product) {
	r.db.Table(TableProducts).Insert(store.Row{
		"tenant_id": p.TenantID,
		"sku":       p.SKU,
		"name":      p.Name,
		"on_hand":   p.OnHand,
		"reserved":  p.Reserved,
	})
}

// Get returns the product for a tenant/sku pair and whether it was found.
func (r *ProductRepo) Get(tenantID, sku string) (model.Product, bool) {
	rows := store.Filter(r.db.Table(TableProducts).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID && store.AsString(row, "sku") == sku
	})
	if len(rows) == 0 {
		return model.Product{}, false
	}
	row := rows[0]
	return model.Product{
		TenantID: store.AsString(row, "tenant_id"),
		SKU:      store.AsString(row, "sku"),
		Name:     store.AsString(row, "name"),
		OnHand:   store.AsInt(row, "on_hand"),
		Reserved: store.AsInt(row, "reserved"),
	}, true
}
