// Hidden behavioural check for hold expiry and partial fulfillment (stage 2).
//
// Building on holds, this stage adds two behaviours:
//   - a hold can carry an expiry, and expiring holds whose time has passed frees
//     their stock while leaving unexpired and never-expiring holds untouched;
//   - a hold can be fulfilled in part: fulfilling some units draws those units
//     down from on-hand stock and frees them from the reservation, leaving the
//     rest of the hold live, and fulfilling the remainder closes the hold.
// This program drives the public hold service and asserts those behaviours.
// Exits non-zero on any failure.
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
	products  *repository.ProductRepo
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
		products:  pr,
	}
}

func avail(s scenario, sku string) int {
	n, _ := s.inventory.Available("A", sku)
	return n
}

func onHand(s scenario, sku string) int {
	p, _ := s.products.Get("A", sku)
	return p.OnHand
}

func main() {
	// --- expiry ---------------------------------------------------------

	// 1. A hold past its expiry is released by ExpireBefore; its stock comes back.
	{
		s := newScenario()
		_, _ = s.holds.PlaceUntil("A", "W", 20, "2026-01-01", "2026-01-10")
		check("placed hold reduces availability", avail(s, "W") == 80)
		n := s.holds.ExpireBefore("2026-01-15")
		check("an expired hold is released", n == 1)
		check("expiring a hold restores its stock", avail(s, "W") == 100)
		check("an expired hold is removed", len(s.holds.List("A")) == 0)
	}

	// 2. ExpireBefore leaves unexpired and never-expiring holds alone.
	{
		s := newScenario()
		_, _ = s.holds.PlaceUntil("A", "W", 10, "2026-01-01", "2026-02-01") // expires later
		_, _ = s.holds.Place("A", "G", 4, "2026-01-01")                     // never expires
		n := s.holds.ExpireBefore("2026-01-15")
		check("nothing expires before its time", n == 0)
		check("unexpired hold still ties up stock", avail(s, "W") == 90)
		check("never-expiring hold still ties up stock", avail(s, "G") == 6)
		check("no holds were removed early", len(s.holds.List("A")) == 2)
	}

	// 3. A hold whose expiry equals the cutoff expires (boundary is inclusive).
	{
		s := newScenario()
		_, _ = s.holds.PlaceUntil("A", "W", 5, "2026-01-01", "2026-01-15")
		n := s.holds.ExpireBefore("2026-01-15")
		check("a hold expiring exactly at the cutoff is released", n == 1)
		check("boundary expiry restores stock", avail(s, "W") == 100)
	}

	// --- partial fulfillment -------------------------------------------

	// 4. Fulfilling part of a hold draws those units from on-hand and frees the
	//    reservation for them, leaving the rest of the hold live.
	{
		s := newScenario()
		h, _ := s.holds.Place("A", "W", 30, "2026-01-01")
		err := s.holds.Fulfill(h.ID, 10)
		check("partial fulfillment succeeds", err == nil)
		check("fulfilled units leave on-hand stock", onHand(s, "W") == 90)
		// 30 reserved, 10 fulfilled -> 20 still reserved against 90 on-hand -> 70 available.
		check("partial fulfillment frees the fulfilled units' reservation", avail(s, "W") == 70)
		live := s.holds.List("A")
		check("the hold stays live after partial fulfillment", len(live) == 1)
		if len(live) == 1 {
			check("the hold shrinks by the fulfilled amount", live[0].Quantity == 20)
		}
	}

	// 5. Fulfilling the remaining units closes the hold entirely.
	{
		s := newScenario()
		h, _ := s.holds.Place("A", "W", 30, "2026-01-01")
		_ = s.holds.Fulfill(h.ID, 10)
		err := s.holds.Fulfill(h.ID, 20)
		check("fulfilling the remainder succeeds", err == nil)
		check("all fulfilled units have left on-hand stock", onHand(s, "W") == 70)
		check("no reservation remains once the hold is fully fulfilled", avail(s, "W") == 70)
		check("a fully fulfilled hold is removed", len(s.holds.List("A")) == 0)
	}

	// 6. Fulfilling more than remains fulfills the whole hold, no more.
	{
		s := newScenario()
		h, _ := s.holds.Place("A", "G", 4, "2026-01-01")
		err := s.holds.Fulfill(h.ID, 99)
		check("over-fulfilling closes the hold without error", err == nil)
		check("over-fulfillment draws down only the held units", onHand(s, "G") == 6)
		check("over-fulfillment leaves no reservation", avail(s, "G") == 6)
		check("over-fulfilled hold is removed", len(s.holds.List("A")) == 0)
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
