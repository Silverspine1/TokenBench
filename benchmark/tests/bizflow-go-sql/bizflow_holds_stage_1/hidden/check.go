// Hidden behavioural check for inventory holds (stage 1).
//
// A hold is a temporary stock reservation that is not tied to an invoice. While
// a hold is live it must reduce the available stock of its product; releasing
// the hold must give that stock back. Placing a hold must be all-or-nothing and
// must never reserve more than is available. This program drives the public hold
// service and asserts those behaviours. Exits non-zero on any failure.
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
	holds     *service.HoldService
	inventory *service.InventoryService
}

func newScenario() scenario {
	db := store.NewDB()
	pr := repository.NewProductRepo(db)
	pr.Insert(model.Product{TenantID: "A", SKU: "W", Name: "Widget", OnHand: 100, Reserved: 0})
	pr.Insert(model.Product{TenantID: "A", SKU: "G", Name: "Gadget", OnHand: 10, Reserved: 0})
	return scenario{
		db:        db,
		holds:     service.NewHoldService(db),
		inventory: service.NewInventoryService(db),
	}
}

func avail(s scenario, sku string) int {
	n, _ := s.inventory.Available("A", sku)
	return n
}

func main() {
	// 1. Placing a hold reduces available stock by the held quantity.
	{
		s := newScenario()
		_, err := s.holds.Place("A", "W", 30, "2026-01-01")
		check("placing a hold succeeds", err == nil)
		check("placing a hold reduces available stock", avail(s, "W") == 70)
	}

	// 2. Releasing a hold gives the reserved stock back.
	{
		s := newScenario()
		h, _ := s.holds.Place("A", "W", 30, "2026-01-01")
		err := s.holds.Release(h.ID)
		check("releasing a hold succeeds", err == nil)
		check("releasing a hold restores available stock", avail(s, "W") == 100)
	}

	// 3. A hold that asks for more than is available fails and reserves nothing.
	{
		s := newScenario()
		_, err := s.holds.Place("A", "G", 999, "2026-01-01")
		check("over-stock hold fails", err != nil)
		check("over-stock hold reserves no stock", avail(s, "G") == 10)
		check("over-stock hold records no hold", len(s.holds.List("A")) == 0)
	}

	// 4. Two holds on the same product stack: combined they reduce availability,
	//    and releasing one frees only its own units.
	{
		s := newScenario()
		h1, _ := s.holds.Place("A", "G", 4, "2026-01-01")
		_, _ = s.holds.Place("A", "G", 3, "2026-01-02")
		check("two holds stack on availability", avail(s, "G") == 3)
		_ = s.holds.Release(h1.ID)
		check("releasing one hold frees only its units", avail(s, "G") == 7)
		check("the other hold is still live", len(s.holds.List("A")) == 1)
	}

	// 5. A second hold cannot reserve stock a live hold already ties up.
	{
		s := newScenario()
		_, _ = s.holds.Place("A", "G", 8, "2026-01-01")
		_, err := s.holds.Place("A", "G", 5, "2026-01-02")
		check("a hold cannot reserve already-held stock", err != nil)
		check("the rejected hold leaves availability unchanged", avail(s, "G") == 2)
	}

	// 6. Releasing an unknown hold fails and changes nothing.
	{
		s := newScenario()
		_, _ = s.holds.Place("A", "W", 10, "2026-01-01")
		err := s.holds.Release("hold-nope")
		check("releasing an unknown hold fails", err != nil)
		check("a failed release leaves availability unchanged", avail(s, "W") == 90)
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
