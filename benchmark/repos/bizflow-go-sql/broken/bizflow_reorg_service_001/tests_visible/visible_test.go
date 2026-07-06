package tests_visible

import (
	"testing"

	"bizflow/internal/bizdb"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// The reorg visible smoke check exercises only the stable data-access seam that
// is present in every layout: opening the seeded database and reading invoices
// and products back through the repository. It does not import the
// business-logic packages, so it compiles and passes regardless of how those
// packages are arranged.

// Opening the seeded database yields the expected invoice rows for a tenant.
func TestSeededInvoicesReadBack(t *testing.T) {
	db, err := bizdb.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	repo := repository.NewInvoiceRepo(db)
	rows := repo.ListByTenant("t_acme")
	if len(rows) != 3 {
		t.Fatalf("expected 3 invoices for t_acme, got %d", len(rows))
	}
}

// The product data access seam reports the seeded on-hand stock.
func TestSeededProductOnHand(t *testing.T) {
	db, err := bizdb.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	pr := repository.NewProductRepo(db)
	p, ok := pr.Get("t_acme", "WIDGET")
	if !ok {
		t.Fatalf("WIDGET missing for t_acme")
	}
	if p.OnHand != 100 {
		t.Fatalf("expected WIDGET on_hand 100, got %d", p.OnHand)
	}
}

// Paging a tenant's invoices walks every row once, in order.
func TestInvoicePagingVisitsEveryRow(t *testing.T) {
	db, err := bizdb.Open()
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	repo := repository.NewInvoiceRepo(db)
	seen := map[string]bool{}
	cursor := 0
	for {
		page := repo.PageByTenant("t_acme", cursor, 2)
		for _, row := range page.Rows {
			seen[store.AsString(row, "id")] = true
		}
		if !page.HasMore {
			break
		}
		cursor = page.NextCursor
	}
	if len(seen) != 3 {
		t.Fatalf("expected to page 3 distinct invoices, got %d", len(seen))
	}
}
