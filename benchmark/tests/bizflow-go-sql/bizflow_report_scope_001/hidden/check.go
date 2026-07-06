// Hidden behavioural check for the tenant revenue report.
//
// It builds a two-tenant scenario through the public repository API and asserts
// the report's contract: a tenant sees every one of its own invoices (including
// invoices with no payments yet), never another tenant's invoices, with payments
// summed per invoice and rows ordered by issue date then id. The program exits
// non-zero if any case fails. It is copied into the candidate module as a package
// and run with `go run`.
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

func line(sku string, qty, cents int) model.InvoiceLine {
	return model.InvoiceLine{SKU: sku, Quantity: qty, UnitCents: cents}
}

func rowByID(rows []model.ReportRow, id string) (model.ReportRow, bool) {
	for _, r := range rows {
		if r.InvoiceID == id {
			return r, true
		}
	}
	return model.ReportRow{}, false
}

func main() {
	db := store.NewDB()
	ir := repository.NewInvoiceRepo(db)
	pr := repository.NewPaymentRepo(db)
	rr := repository.NewReportRepo(db)

	// Tenant A: one paid, one partial (two payments), one with no payment yet.
	ir.Insert(model.Invoice{ID: "a1", TenantID: "A", Customer: "CA1", Status: "paid", IssuedAt: "2026-01-01", Lines: []model.InvoiceLine{line("X", 2, 500)}}) // total 1000
	ir.Insert(model.Invoice{ID: "a3", TenantID: "A", Customer: "CA3", Status: "open", IssuedAt: "2026-01-02", Lines: []model.InvoiceLine{line("X", 4, 500)}}) // total 2000
	ir.Insert(model.Invoice{ID: "a2", TenantID: "A", Customer: "CA2", Status: "open", IssuedAt: "2026-01-03", Lines: []model.InvoiceLine{line("X", 1, 700)}}) // total 700
	// Tenant A also has a cancelled invoice; it is not revenue and must be left out.
	ir.Insert(model.Invoice{ID: "a4", TenantID: "A", Customer: "CA4", Status: "void", IssuedAt: "2026-01-02", Lines: []model.InvoiceLine{line("X", 8, 500)}}) // total 4000, cancelled
	// Tenant B: must never appear in tenant A's report.
	ir.Insert(model.Invoice{ID: "b1", TenantID: "B", Customer: "CB1", Status: "paid", IssuedAt: "2026-01-01", Lines: []model.InvoiceLine{line("Y", 1, 999)}})

	pr.Insert(model.Payment{ID: "p1", InvoiceID: "a1", TenantID: "A", AmountCents: 1000, PaidAt: "2026-01-02"})
	pr.Insert(model.Payment{ID: "p2", InvoiceID: "a3", TenantID: "A", AmountCents: 500, PaidAt: "2026-01-03"})
	pr.Insert(model.Payment{ID: "p3", InvoiceID: "a3", TenantID: "A", AmountCents: 300, PaidAt: "2026-01-04"})
	// A payment recorded against the cancelled invoice still must not pull it in.
	pr.Insert(model.Payment{ID: "p5", InvoiceID: "a4", TenantID: "A", AmountCents: 1500, PaidAt: "2026-01-05"})
	pr.Insert(model.Payment{ID: "p4", InvoiceID: "b1", TenantID: "B", AmountCents: 999, PaidAt: "2026-01-02"})

	rows := rr.TenantRevenue("A")

	// 1. Exactly tenant A's three billable invoices are reported (the cancelled one is not).
	check("reports exactly the tenant's three billable invoices", len(rows) == 3)

	// 1b. The cancelled invoice never appears, even though a payment exists for it.
	_, hasVoid := rowByID(rows, "a4")
	check("cancelled invoice never appears as a row", !hasVoid)

	// 2. The unpaid invoice is present with paid=0 and full amount due.
	a2, hasA2 := rowByID(rows, "a2")
	check("unpaid invoice a2 is present", hasA2)
	if hasA2 {
		check("unpaid invoice reports paid_cents=0", a2.PaidCents == 0)
		check("unpaid invoice reports full amount due", a2.DueCents == 700)
	}

	// 3. The fully paid invoice reports paid in full, nothing due.
	a1, hasA1 := rowByID(rows, "a1")
	check("paid invoice a1 is present", hasA1)
	if hasA1 {
		check("paid invoice reports paid_cents=1000", a1.PaidCents == 1000)
		check("paid invoice reports due_cents=0", a1.DueCents == 0)
	}

	// 4. Multiple payments on one invoice are summed.
	a3, hasA3 := rowByID(rows, "a3")
	check("partly paid invoice a3 is present", hasA3)
	if hasA3 {
		check("two payments are summed to 800", a3.PaidCents == 800)
		check("remaining due is 1200", a3.DueCents == 1200)
	}

	// 5. No other tenant's invoice leaks into the report.
	_, hasB := rowByID(rows, "b1")
	check("another tenant's invoice never appears", !hasB)

	// 6. Rows are ordered by issue date then id: a1, a3, a2.
	gotOrder := make([]string, 0, len(rows))
	for _, r := range rows {
		gotOrder = append(gotOrder, r.InvoiceID)
	}
	check("rows ordered by issue date then id", fmt.Sprint(gotOrder) == fmt.Sprint([]string{"a1", "a3", "a2"}))

	// 7. Headline totals roll up the per-row figures for the tenant only, with the
	//    cancelled invoice (and its payment) excluded from every figure.
	total, paid, due := rr.TenantTotals("A")
	check("tenant total is 3700", total == 3700)
	check("tenant paid is 1800", paid == 1800)
	check("tenant due is 1900", due == 1900)

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
