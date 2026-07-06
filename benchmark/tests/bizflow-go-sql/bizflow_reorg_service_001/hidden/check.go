// Hidden behavioural check for the bizflow service reorganization.
//
// A correct reorganization relocates the invoice + inventory logic into the
// canonical internal/service package and the reporting logic into the canonical
// internal/reports package, each exporting the public identifiers below. This
// program imports those two canonical packages directly and asserts the
// behaviour is unchanged. If either package does not exist at its canonical
// import path, this program fails to compile and the hidden test fails. Exits
// non-zero on any failure.
package main

import (
	"fmt"
	"os"

	"bizflow/internal/bizdb"
	"bizflow/internal/model"
	"bizflow/internal/reports"
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

func findRow(rows []model.ReportRow, id string) (model.ReportRow, bool) {
	for _, r := range rows {
		if r.InvoiceID == id {
			return r, true
		}
	}
	return model.ReportRow{}, false
}

func main() {
	// --- internal/service: invoice creation + inventory reservation -----
	{
		db := store.NewDB()
		pr := repository.NewProductRepo(db)
		pr.Insert(model.Product{TenantID: "A", SKU: "W", Name: "Widget", OnHand: 100, Reserved: 0})

		inv := service.NewInvoiceService(db)
		inventory := service.NewInventoryService(db)

		// A creation within stock succeeds and reserves the requested units.
		_, err := inv.Create("A", "Cust1", "2026-01-01", []model.InvoiceLine{{SKU: "W", Quantity: 5, UnitCents: 500}})
		check("service: valid creation succeeds", err == nil)
		avail, _ := inventory.Available("A", "W")
		check("service: valid creation reserves stock", avail == 95)

		// A creation whose line overflows stock fails and reserves nothing.
		_, err = inv.Create("A", "Cust2", "2026-01-02", []model.InvoiceLine{{SKU: "W", Quantity: 999, UnitCents: 100}})
		check("service: over-stock creation fails", err != nil)
		avail, _ = inventory.Available("A", "W")
		check("service: failed creation reserves no stock", avail == 95)
	}

	// --- internal/reports: revenue rows + status summary ----------------
	{
		db, err := bizdb.Open()
		if err != nil {
			fmt.Printf("not ok - reports: open seeded db (%v)\n", err)
			failures++
		} else {
			rs := reports.NewService(db)
			report := rs.TenantReport("t_acme")

			// A paid invoice reports its figures, an unpaid one shows full due.
			row, ok := findRow(report.Rows, "inv-1001")
			check("reports: paid invoice figures correct",
				ok && row.TotalCents == 5000 && row.PaidCents == 5000 && row.DueCents == 0)

			open, ok := findRow(report.Rows, "inv-1003")
			check("reports: unpaid invoice shows full amount due",
				ok && open.PaidCents == 0 && open.DueCents == open.TotalCents && open.TotalCents == 3000)

			// The report is tenant-scoped: no other tenant's rows leak in.
			_, leaked := findRow(report.Rows, "inv-2001")
			check("reports: report is scoped to the tenant", !leaked)

			// Status summary tallies the tenant's invoices by status.
			summary := rs.StatusSummary("t_acme")
			byStatus := map[string]reports.StatusRow{}
			for _, s := range summary {
				byStatus[s.Status] = s
			}
			check("reports: status summary counts open invoices", byStatus["open"].Count == 2)
		}
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
