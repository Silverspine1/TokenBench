// Hidden behavioural check for the per-status invoice summary.
//
// StatusSummary groups a tenant's invoices by status, counting the invoices and
// summing their totals, scoped to that tenant only. This program builds a
// two-tenant scenario and asserts the counts, totals, scoping and ordering.
// Exits non-zero on failure.
package main

import (
	"fmt"
	"os"

	"bizflow/internal/model"
	"bizflow/internal/repository"
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

func inv(id, tenant, status string, cents int) model.Invoice {
	return model.Invoice{
		ID: id, TenantID: tenant, Customer: "C", Status: status, IssuedAt: "2026-01-01",
		Lines: []model.InvoiceLine{{SKU: "X", Quantity: 1, UnitCents: cents}},
	}
}

func rowFor(rows []repository.StatusRow, status string) (repository.StatusRow, bool) {
	for _, r := range rows {
		if r.Status == status {
			return r, true
		}
	}
	return repository.StatusRow{}, false
}

func main() {
	db := store.NewDB()
	ir := repository.NewInvoiceRepo(db)
	rr := repository.NewReportRepo(db)

	// Tenant A: three open, two paid, one void.
	ir.Insert(inv("a1", "A", "open", 100))
	ir.Insert(inv("a2", "A", "open", 200))
	ir.Insert(inv("a3", "A", "open", 300))
	ir.Insert(inv("a4", "A", "paid", 50))
	ir.Insert(inv("a5", "A", "paid", 150))
	ir.Insert(inv("a6", "A", "void", 400))
	// Tenant B: five open invoices that must not affect tenant A's summary.
	for i := 0; i < 5; i++ {
		ir.Insert(inv(fmt.Sprintf("b%d", i), "B", "open", 1000))
	}

	rows := rr.StatusSummary("A")

	// 1. Exactly three statuses are reported for tenant A.
	check("exactly three statuses are reported", len(rows) == 3)

	// 2. Open invoices are counted and totalled correctly.
	open, hasOpen := rowFor(rows, "open")
	check("open status present", hasOpen)
	check("open count is 3", open.Count == 3)
	check("open total is 600", open.TotalCents == 600)

	// 3. Paid invoices are counted and totalled correctly.
	paid, hasPaid := rowFor(rows, "paid")
	check("paid status present", hasPaid)
	check("paid count is 2", paid.Count == 2)
	check("paid total is 200", paid.TotalCents == 200)

	// 4. Void invoices are counted and totalled correctly.
	void, hasVoid := rowFor(rows, "void")
	check("void status present", hasVoid)
	check("void count is 1", void.Count == 1)
	check("void total is 400", void.TotalCents == 400)

	// 5. Another tenant's invoices do not inflate the counts.
	check("other tenant invoices are excluded from open count", open.Count == 3)

	// 6. Rows are ordered by status.
	ordered := true
	for i := 1; i < len(rows); i++ {
		if rows[i-1].Status > rows[i].Status {
			ordered = false
		}
	}
	check("rows are ordered by status", ordered)

	// 7. A status the tenant has none of never appears as a row.
	_, hasDraft := rowFor(rows, "draft")
	check("a status with no invoices for the tenant is absent", !hasDraft)

	// 8. Reconciliation: the per-status counts and totals add up to the tenant's
	//    own invoice count and overall invoice total, and nothing else. Tenant A
	//    has six invoices summing to 1200; the summary must account for exactly
	//    that and no more.
	countSum, centsSum := 0, 0
	for _, row := range rows {
		countSum += row.Count
		centsSum += row.TotalCents
	}
	check("per-status counts reconcile to the tenant's invoice count", countSum == 6)
	check("per-status totals reconcile to the tenant's overall total", centsSum == 1200)

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
