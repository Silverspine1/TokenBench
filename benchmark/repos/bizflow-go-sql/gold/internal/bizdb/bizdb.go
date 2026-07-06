// Package bizdb opens a ready-to-use database: it applies the schema migrations
// and seeds the deterministic fixture data.
package bizdb

import (
	"encoding/json"
	"io/fs"

	"bizflow"
	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
	"bizflow/migrations"
)

// Open returns a fully migrated and seeded database.
func Open() (*store.DB, error) {
	db := store.NewDB()
	migrations.Apply(db)
	if err := Seed(db, bizflow.FixturesFS); err != nil {
		return nil, err
	}
	return db, nil
}

// Seed loads the fixture JSON from fsys into db. It is safe to call on a freshly
// migrated database.
func Seed(db *store.DB, fsys fs.FS) error {
	var products []model.Product
	if err := load(fsys, "fixtures/products.json", &products); err != nil {
		return err
	}
	var invoices []model.Invoice
	if err := load(fsys, "fixtures/invoices.json", &invoices); err != nil {
		return err
	}
	var payments []model.Payment
	if err := load(fsys, "fixtures/payments.json", &payments); err != nil {
		return err
	}

	productRepo := repository.NewProductRepo(db)
	for _, p := range products {
		productRepo.Insert(p)
	}
	invoiceRepo := repository.NewInvoiceRepo(db)
	for _, inv := range invoices {
		invoiceRepo.Insert(inv)
	}
	paymentRepo := repository.NewPaymentRepo(db)
	for _, p := range payments {
		paymentRepo.Insert(p)
	}
	return nil
}

func load(fsys fs.FS, name string, dst any) error {
	data, err := fs.ReadFile(fsys, name)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, dst)
}
