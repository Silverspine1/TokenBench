// Hidden behavioural check for invoice creation atomicity.
//
// Creating an invoice reserves stock for each line. The whole operation must be
// all-or-nothing: if any line cannot be reserved, no invoice is stored and no
// stock stays reserved. This program drives the public services and asserts that
// a failed creation leaves the database exactly as it was. Exits non-zero on any
// failure.
package main

import (
	"fmt"
	"os"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/service"
	"bizflow/internal/store"
)

var failures int

func check(name string, cond bool) {
	if cond {
		fmt.Printf("ok - %s\n", name)
		return
	}
	fmt.Printf("not ok - %s\n", name)
	failures++
}

type scenario struct {
	db        *store.DB
	invoices  *service.InvoiceService
	inventory *service.InventoryService
	repo      *repository.InvoiceRepo
}

// newScenario builds a fresh database with two products in stock.
func newScenario() scenario {
	db := store.NewDB()
	pr := repository.NewProductRepo(db)
	pr.Insert(model.Product{TenantID: "A", SKU: "W", Name: "Widget", OnHand: 100, Reserved: 0})
	pr.Insert(model.Product{TenantID: "A", SKU: "G", Name: "Gadget", OnHand: 10, Reserved: 0})
	return scenario{
		db:        db,
		invoices:  service.NewInvoiceService(db),
		inventory: service.NewInventoryService(db),
		repo:      repository.NewInvoiceRepo(db),
	}
}

func line(sku string, qty, cents int) model.InvoiceLine {
	return model.InvoiceLine{SKU: sku, Quantity: qty, UnitCents: cents}
}

func avail(s scenario, sku string) int {
	n, _ := s.inventory.Available("A", sku)
	return n
}

func main() {
	// 1. A creation that fits stock succeeds and reserves the requested units.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Cust1", "2026-01-01", []model.InvoiceLine{line("W", 5, 500)})
		check("valid creation succeeds", err == nil)
		check("valid creation reserves stock", avail(s, "W") == 95)
		check("valid creation stores one invoice", len(s.repo.ListByTenant("A")) == 1)
	}

	// 2. A creation whose second line overflows stock fails and reserves nothing.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Cust2", "2026-01-02",
			[]model.InvoiceLine{line("W", 5, 500), line("G", 999, 100)})
		check("over-stock creation fails", err != nil)
		check("failed creation reserves no stock for the first line", avail(s, "W") == 100)
		check("failed creation does not reduce the overflowing product", avail(s, "G") == 10)
		check("failed creation stores no invoice", len(s.repo.ListByTenant("A")) == 0)
	}

	// 3. A creation referencing an unknown product mid-order rolls back fully.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Cust3", "2026-01-03",
			[]model.InvoiceLine{line("W", 3, 500), line("Z", 1, 100)})
		check("unknown-product creation fails", err != nil)
		check("unknown-product creation reserves no stock", avail(s, "W") == 100)
		check("unknown-product creation stores no invoice", len(s.repo.ListByTenant("A")) == 0)
	}

	// 4. After a failed creation the database is still usable: a later valid
	//    creation succeeds and reserves from the original stock.
	{
		s := newScenario()
		_, _ = s.invoices.Create("A", "Bad", "2026-01-04",
			[]model.InvoiceLine{line("G", 999, 100)})
		_, err := s.invoices.Create("A", "Good", "2026-01-05", []model.InvoiceLine{line("G", 4, 100)})
		check("a valid creation after a failed one succeeds", err == nil)
		check("the later creation reserves from full stock", avail(s, "G") == 6)
		check("only the successful invoice is stored", len(s.repo.ListByTenant("A")) == 1)
	}

	// 5. A three-line order whose last line fails reserves none of the earlier lines.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Cust5", "2026-01-06",
			[]model.InvoiceLine{line("W", 2, 500), line("G", 3, 100), line("G", 50, 100)})
		check("multi-line order with a failing last line fails", err != nil)
		check("multi-line failure reserves no W", avail(s, "W") == 100)
		check("multi-line failure reserves no G", avail(s, "G") == 10)
	}

	// 6. Two lines of the SAME product that each fit on their own but together
	//    exceed the stock: the creation must fail and reserve nothing. With only
	//    10 on hand, two lines of 6 each are fine alone (6 <= 10) but 12 > 10.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Cust6", "2026-01-07",
			[]model.InvoiceLine{line("G", 6, 100), line("G", 6, 100)})
		check("same-product lines that together overflow are rejected", err != nil)
		check("same-product overflow reserves no stock at all", avail(s, "G") == 10)
		check("same-product overflow stores no invoice", len(s.repo.ListByTenant("A")) == 0)
	}

	// 7. A failed creation must not consume an invoice number: the next successful
	//    creation takes the number the failed attempt would have used, leaving no
	//    gap in the numbering.
	{
		s := newScenario()
		_, err := s.invoices.Create("A", "Bad", "2026-01-08",
			[]model.InvoiceLine{line("G", 999, 100)})
		check("over-stock creation fails", err != nil)
		good, err2 := s.invoices.Create("A", "Good", "2026-01-09", []model.InvoiceLine{line("G", 1, 100)})
		check("a later valid creation succeeds", err2 == nil)
		check("the failed attempt left no gap in invoice numbering", good.ID == "inv-0001")
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
