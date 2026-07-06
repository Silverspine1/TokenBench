// Package migrations defines the database schema and applies it to a store.
//
// Each migration is a named step that creates the tables and declares the
// columns the repositories rely on. The set of applied migrations is recorded in
// the schema_migrations table so a second Apply is a no-op.
package migrations

import (
	"bizflow/internal/store"
)

// Migration is one ordered schema step.
type Migration struct {
	ID    string
	Apply func(db *store.DB)
}

// All returns the ordered list of migrations that define the current schema.
func All() []Migration {
	return []Migration{
		{
			ID: "0001_init",
			Apply: func(db *store.DB) {
				db.CreateTable("tenants", "id", "name")
				db.CreateTable("products", "tenant_id", "sku", "name", "on_hand", "reserved")
				db.CreateTable("invoices", "id", "tenant_id", "customer", "status", "issued_at", "total_cents")
				db.CreateTable("payments", "id", "invoice_id", "tenant_id", "amount_cents", "paid_at")
			},
		},
		{
			ID: "0002_indexes",
			Apply: func(db *store.DB) {
				// The in-memory store does not need physical indexes; this
				// migration exists to mirror the SQL schema and is a no-op.
			},
		},
		{
			ID: "0003_holds",
			Apply: func(db *store.DB) {
				// Holds are temporary stock reservations that do not (yet) belong
				// to an invoice. A hold ties up units of a product for a tenant.
				db.CreateTable("holds", "id", "tenant_id", "sku", "quantity", "created_at", "expires_at")
			},
		},
	}
}

// Apply runs every migration that has not yet been recorded, in order.
func Apply(db *store.DB) {
	applied := db.CreateTable("schema_migrations", "id")
	seen := map[string]bool{}
	for _, row := range applied.All() {
		seen[store.AsString(row, "id")] = true
	}
	for _, m := range All() {
		if seen[m.ID] {
			continue
		}
		m.Apply(db)
		applied.Insert(store.Row{"id": m.ID})
	}
}
