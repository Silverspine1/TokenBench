// Hidden behavioural check for tenant invoice pagination.
//
// A tenant's invoices are paged in issue-date-then-id order. Paging from cursor
// 0 and following NextCursor must visit every invoice exactly once, in order,
// with nothing skipped or repeated at a page boundary. This program inserts
// invoices whose insertion order differs from their issue order and asserts the
// paging contract. Exits non-zero on failure.
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

func newRepo() *repository.InvoiceRepo {
	db := store.NewDB()
	r := repository.NewInvoiceRepo(db)
	// Insertion order is deliberately not issue order.
	r.Insert(model.Invoice{ID: "inv-c", TenantID: "A", Customer: "C", Status: "open", IssuedAt: "2026-01-05"})
	r.Insert(model.Invoice{ID: "inv-a", TenantID: "A", Customer: "A", Status: "open", IssuedAt: "2026-01-01"})
	r.Insert(model.Invoice{ID: "inv-b", TenantID: "A", Customer: "B", Status: "open", IssuedAt: "2026-01-03"})
	r.Insert(model.Invoice{ID: "inv-d", TenantID: "A", Customer: "D", Status: "open", IssuedAt: "2026-01-04"})
	r.Insert(model.Invoice{ID: "inv-e", TenantID: "A", Customer: "E", Status: "open", IssuedAt: "2026-01-02"})
	// Another tenant's invoice must never appear in A's pages.
	r.Insert(model.Invoice{ID: "inv-z", TenantID: "B", Customer: "Z", Status: "open", IssuedAt: "2026-01-01"})
	return r
}

func ids(rows []store.Row) []string {
	out := make([]string, 0, len(rows))
	for _, row := range rows {
		out = append(out, store.AsString(row, "id"))
	}
	return out
}

func eq(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func main() {
	want := []string{"inv-a", "inv-e", "inv-b", "inv-d", "inv-c"}
	r := newRepo()

	// 1. Paging with a small limit and following NextCursor visits all rows in
	//    order with no skip or duplicate.
	{
		var got []string
		cursor := 0
		for step := 0; step < 50; step++ {
			p := r.PageByTenant("A", cursor, 2)
			got = append(got, ids(p.Rows)...)
			if !p.HasMore {
				break
			}
			cursor = p.NextCursor
		}
		check("paging visits every invoice in order, no skip or duplicate", eq(got, want))
		check("paging returns exactly the tenant's five invoices", len(got) == 5)
	}

	// 2. The first page is the first slice of the ordered list.
	check("first page is the earliest two invoices", eq(ids(r.PageByTenant("A", 0, 2).Rows), []string{"inv-a", "inv-e"}))

	// 3. Ordering: the first invoice is the earliest issued, not the first inserted.
	{
		first := r.PageByTenant("A", 0, 1).Rows
		check("first invoice is the earliest issued", len(first) == 1 && store.AsString(first[0], "id") == "inv-a")
	}

	// 4. A page that starts past the end is empty.
	check("a page past the end is empty", len(r.PageByTenant("A", 99, 2).Rows) == 0)

	// 5. A limit larger than the set returns the whole ordered set and reports no more.
	{
		p := r.PageByTenant("A", 0, 100)
		check("an oversize limit returns the whole ordered set", eq(ids(p.Rows), want))
		check("an oversize limit reports no more pages", !p.HasMore)
	}

	// 6. Another tenant's invoice never appears in this tenant's pages.
	{
		var got []string
		cursor := 0
		for step := 0; step < 50; step++ {
			p := r.PageByTenant("A", cursor, 2)
			got = append(got, ids(p.Rows)...)
			if !p.HasMore {
				break
			}
			cursor = p.NextCursor
		}
		seenZ := false
		for _, id := range got {
			if id == "inv-z" {
				seenZ = true
			}
		}
		check("another tenant's invoice never appears", !seenZ)
	}

	// 7. Exact-multiple boundary: when the row count is an exact multiple of the
	//    page size, walking the pages ends cleanly with no extra empty page and
	//    nothing skipped or repeated. Tenant E has exactly four invoices; paging
	//    two at a time must yield two full pages and then stop.
	{
		db := store.NewDB()
		er := repository.NewInvoiceRepo(db)
		er.Insert(model.Invoice{ID: "e1", TenantID: "E", Customer: "C", Status: "open", IssuedAt: "2026-02-01"})
		er.Insert(model.Invoice{ID: "e2", TenantID: "E", Customer: "C", Status: "open", IssuedAt: "2026-02-02"})
		er.Insert(model.Invoice{ID: "e3", TenantID: "E", Customer: "C", Status: "open", IssuedAt: "2026-02-03"})
		er.Insert(model.Invoice{ID: "e4", TenantID: "E", Customer: "C", Status: "open", IssuedAt: "2026-02-04"})
		var got []string
		pages := 0
		cursor := 0
		for step := 0; step < 50; step++ {
			p := er.PageByTenant("E", cursor, 2)
			pages++
			got = append(got, ids(p.Rows)...)
			if !p.HasMore {
				break
			}
			cursor = p.NextCursor
		}
		check("exact-multiple paging visits every row once", eq(got, []string{"e1", "e2", "e3", "e4"}))
		check("exact-multiple paging makes no empty trailing page", pages == 2)
	}

	// 8. Stable tie-break: invoices sharing the same issue date are ordered by id,
	//    and that order is stable across page boundaries.
	{
		db := store.NewDB()
		tr := repository.NewInvoiceRepo(db)
		// Same issue date for all; insertion order is deliberately scrambled.
		tr.Insert(model.Invoice{ID: "t3", TenantID: "T", Customer: "C", Status: "open", IssuedAt: "2026-03-01"})
		tr.Insert(model.Invoice{ID: "t1", TenantID: "T", Customer: "C", Status: "open", IssuedAt: "2026-03-01"})
		tr.Insert(model.Invoice{ID: "t4", TenantID: "T", Customer: "C", Status: "open", IssuedAt: "2026-03-01"})
		tr.Insert(model.Invoice{ID: "t2", TenantID: "T", Customer: "C", Status: "open", IssuedAt: "2026-03-01"})
		var got []string
		cursor := 0
		for step := 0; step < 50; step++ {
			p := tr.PageByTenant("T", cursor, 2)
			got = append(got, ids(p.Rows)...)
			if !p.HasMore {
				break
			}
			cursor = p.NextCursor
		}
		check("ties on issue date are broken by id, stable across pages", eq(got, []string{"t1", "t2", "t3", "t4"}))
	}

	if failures > 0 {
		fmt.Printf("FAILED: %d check(s)\n", failures)
		os.Exit(1)
	}
	fmt.Println("PASSED")
}
