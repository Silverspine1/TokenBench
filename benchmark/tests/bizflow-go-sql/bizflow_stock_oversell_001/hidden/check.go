// Hidden behavioural check for stock reservation limits.
//
// A product can be reserved up to its available stock (on hand minus what is
// already reserved) and no further. Reservations accumulate, so repeated
// reservations cannot together exceed availability. This program drives the
// public inventory service and asserts those limits. Exits non-zero on failure.
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

// newInv builds a fresh inventory service with one product of the given stock.
func newInv(onHand int) *service.InventoryService {
	db := store.NewDB()
	pr := repository.NewProductRepo(db)
	pr.Insert(model.Product{TenantID: "A", SKU: "G", Name: "Gadget", OnHand: onHand, Reserved: 0})
	return service.NewInventoryService(db)
}

func avail(s *service.InventoryService) int {
	n, _ := s.Available("A", "G")
	return n
}

func main() {
	// 1. Availability starts at the full on-hand quantity.
	{
		s := newInv(10)
		check("availability starts at on hand", avail(s) == 10)
	}

	// 2. A reservation within availability succeeds and lowers availability.
	{
		s := newInv(10)
		check("reserve within stock succeeds", s.Reserve("A", "G", 4) == nil)
		check("availability drops after reserving", avail(s) == 6)
	}

	// 3. Reservations accumulate; an exact-fit reservation is allowed.
	{
		s := newInv(10)
		_ = s.Reserve("A", "G", 4)
		check("second reservation up to the exact remaining is allowed", s.Reserve("A", "G", 6) == nil)
		check("availability reaches zero at the exact fit", avail(s) == 0)
	}

	// 4. A reservation beyond what remains is rejected and changes nothing.
	{
		s := newInv(10)
		_ = s.Reserve("A", "G", 10)
		check("reserving past availability is rejected", s.Reserve("A", "G", 1) != nil)
		check("a rejected reservation leaves availability unchanged", avail(s) == 0)
	}

	// 5. A single reservation larger than stock is rejected up front.
	{
		s := newInv(10)
		check("a reservation larger than stock is rejected", s.Reserve("A", "G", 11) != nil)
		check("the rejected reservation does not consume stock", avail(s) == 10)
	}

	// 6. Two reservations that together exceed availability: the second is rejected.
	{
		s := newInv(10)
		check("first partial reservation succeeds", s.Reserve("A", "G", 7) == nil)
		check("a second reservation that would oversell is rejected", s.Reserve("A", "G", 5) != nil)
		check("availability reflects only the accepted reservation", avail(s) == 3)
	}

	// 7. CheckReservable rejects combined demand that exceeds availability.
	{
		s := newInv(10)
		lines := []model.InvoiceLine{{SKU: "G", Quantity: 6, UnitCents: 1}, {SKU: "G", Quantity: 6, UnitCents: 1}}
		check("combined demand over availability is reported unreservable", s.CheckReservable("A", lines) != nil)
	}

	// 8. CheckReservable must weigh combined same-SKU demand against what is still
	//    available, not the raw on-hand count. With 10 on hand and 4 already
	//    reserved (6 available), two lines of 3 and 4 sum to 7: that is under the
	//    on-hand count but over what remains available, so it must be rejected.
	{
		s := newInv(10)
		_ = s.Reserve("A", "G", 4) // 6 now available
		lines := []model.InvoiceLine{{SKU: "G", Quantity: 3, UnitCents: 1}, {SKU: "G", Quantity: 4, UnitCents: 1}}
		check("combined demand over remaining availability is rejected", s.CheckReservable("A", lines) != nil)
	}

	// 9. CheckReservable still accepts combined same-SKU demand that exactly fits
	//    what remains available.
	{
		s := newInv(10)
		_ = s.Reserve("A", "G", 4) // 6 now available
		lines := []model.InvoiceLine{{SKU: "G", Quantity: 2, UnitCents: 1}, {SKU: "G", Quantity: 4, UnitCents: 1}}
		check("combined demand that exactly fits remaining availability is accepted", s.CheckReservable("A", lines) == nil)
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
