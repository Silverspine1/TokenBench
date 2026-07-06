package tests_visible

import (
	"testing"

	"bizflow/internal/bizdb"
	"bizflow/internal/model"
	"bizflow/internal/service"
)

// findRow returns the report row with the given invoice id.
func findRow(rows []model.ReportRow, id string) (model.ReportRow, bool) {
	for _, r := range rows {
		if r.InvoiceID == id {
			return r, true
		}
	}
	return model.ReportRow{}, false
}

// A fully paid invoice shows up in its tenant's report with the right figures.
// This is a smoke check over the wiring; it does not assert the trickier cases.
func TestPaidInvoiceAppearsInReport(t *testing.T) {
	db, err := bizdb.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	report := service.NewReportService(db).TenantReport("t_acme")
	row, ok := findRow(report.Rows, "inv-1001")
	if !ok {
		t.Fatalf("inv-1001 missing from report")
	}
	if row.TotalCents != 5000 || row.PaidCents != 5000 || row.DueCents != 0 {
		t.Fatalf("inv-1001 figures wrong: %+v", row)
	}
}

// Creating an invoice within stock reserves the requested units.
func TestCreateInvoiceReservesStock(t *testing.T) {
	db, err := bizdb.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	inv := service.NewInvoiceService(db)
	inventory := service.NewInventoryService(db)

	before, _ := inventory.Available("t_acme", "WIDGET")
	_, err = inv.Create("t_acme", "Test Co", "2026-02-01", []model.InvoiceLine{
		{SKU: "WIDGET", Quantity: 5, UnitCents: 500},
	})
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}
	after, _ := inventory.Available("t_acme", "WIDGET")
	if before-after != 5 {
		t.Fatalf("expected 5 units reserved, got %d", before-after)
	}
}
