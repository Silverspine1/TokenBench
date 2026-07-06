// Package legacy is the catch-all package a previous import dropped the
// invoice, inventory and reporting logic into. The three unrelated concerns
// share this one file under terse internal names; a thin set of aliases in
// barrel.go re-exposes them under their original public spellings so callers
// kept compiling. Working in here is awkward because everything is tangled
// together.
package legacy

import (
	"errors"
	"fmt"
	"sort"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// E1 is raised when a reservation asks for more units than are available.
var E1 = errors.New("inventory: insufficient stock")

// E2 is raised when a SKU is not stocked for the tenant.
var E2 = errors.New("inventory: unknown product")

// E3 is raised when an invoice carries no lines.
var E3 = errors.New("invoice: must have at least one line")

// Iv carries stock-level logic for a database handle.
type Iv struct {
	db       *store.DB
	products *repository.ProductRepo
}

// MkIv binds stock logic to db.
func MkIv(db *store.DB) *Iv {
	return &Iv{db: db, products: repository.NewProductRepo(db)}
}

// A reports how many units of sku the tenant can still reserve.
func (s *Iv) A(tenantID, sku string) (int, error) {
	p, ok := s.products.Get(tenantID, sku)
	if !ok {
		return 0, E2
	}
	return p.Available(), nil
}

// R increases the reserved count for one product line. It fails, changing
// nothing, when the product is unknown or there is not enough available stock.
func (s *Iv) R(tenantID, sku string, qty int) error {
	p, ok := s.products.Get(tenantID, sku)
	if !ok {
		return E2
	}
	if qty > p.Available() {
		return E1
	}
	s.db.Table(repository.TableProducts).Update(
		func(row store.Row) bool {
			return store.AsString(row, "tenant_id") == tenantID && store.AsString(row, "sku") == sku
		},
		func(row store.Row) store.Row {
			row["reserved"] = store.AsInt(row, "reserved") + qty
			return row
		},
	)
	return nil
}

// C verifies that the combined demand across lines can be satisfied from current
// availability, without changing any stock.
func (s *Iv) C(tenantID string, lines []model.InvoiceLine) error {
	want := map[string]int{}
	for _, l := range lines {
		want[l.SKU] += l.Quantity
	}
	for sku, qty := range want {
		p, ok := s.products.Get(tenantID, sku)
		if !ok {
			return E2
		}
		if qty > p.Available() {
			return E1
		}
	}
	return nil
}

// Iw creates invoices and reserves the stock they consume.
type Iw struct {
	db        *store.DB
	invoices  *repository.InvoiceRepo
	inventory *Iv
	seq       int
}

// MkIw binds invoice logic to db.
func MkIw(db *store.DB) *Iw {
	return &Iw{
		db:        db,
		invoices:  repository.NewInvoiceRepo(db),
		inventory: MkIv(db),
	}
}

func (s *Iw) n() string {
	s.seq++
	return fmt.Sprintf("inv-%04d", s.seq)
}

// Mk records a new invoice for the tenant and reserves the stock for each line.
// Creation and reservation happen inside a single transaction: if any line
// cannot be reserved, the whole operation is undone, no invoice is stored and no
// stock is reserved. An attempt that does not produce an invoice leaves the
// numbering untouched, so the next successful creation takes the number the
// abandoned attempt would have used.
func (s *Iw) Mk(tenantID, customer, issuedAt string, lines []model.InvoiceLine) (model.Invoice, error) {
	if len(lines) == 0 {
		return model.Invoice{}, E3
	}

	seqBefore := s.seq
	inv := model.Invoice{
		ID:       s.n(),
		TenantID: tenantID,
		Customer: customer,
		Status:   "open",
		IssuedAt: issuedAt,
		Lines:    lines,
	}

	tx := s.db.Begin()
	s.invoices.Insert(inv)
	for _, l := range lines {
		if err := s.inventory.R(tenantID, l.SKU, l.Quantity); err != nil {
			tx.Rollback()
			s.seq = seqBefore
			return model.Invoice{}, err
		}
	}
	if err := tx.Commit(); err != nil {
		s.seq = seqBefore
		return model.Invoice{}, err
	}
	return inv, nil
}

// Rp carries tenant revenue reporting for a database handle.
type Rp struct {
	db *store.DB
}

// MkRp binds reporting logic to db.
func MkRp(db *store.DB) *Rp {
	return &Rp{db: db}
}

// Ts is the headline view of a tenant's revenue.
type Ts struct {
	TenantID   string            `json:"tenant_id"`
	Rows       []model.ReportRow `json:"rows"`
	TotalCents int               `json:"total_cents"`
	PaidCents  int               `json:"paid_cents"`
	DueCents   int               `json:"due_cents"`
}

// T returns every report row for the tenant plus the rolled-up totals.
func (s *Rp) T(tenantID string) Ts {
	rows := s.Rv(tenantID)
	var total, paid, due int
	for _, row := range rows {
		total += row.TotalCents
		paid += row.PaidCents
		due += row.DueCents
	}
	return Ts{
		TenantID:   tenantID,
		Rows:       rows,
		TotalCents: total,
		PaidCents:  paid,
		DueCents:   due,
	}
}

// Rv returns one report row per billable invoice owned by tenantID. Every
// invoice the tenant owns is reported, whether or not any payment has been
// recorded yet; an invoice with no payments reports paid_cents = 0 and the full
// amount still due. Cancelled invoices are not revenue and are left out
// entirely. Rows are ordered by issue date and then invoice id.
func (s *Rp) Rv(tenantID string) []model.ReportRow {
	invoices := store.Filter(s.db.Table(repository.TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID &&
			store.AsString(row, "status") != "void"
	})

	payments := store.Filter(s.db.Table(repository.TablePayments).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
	paid := store.GroupSum(payments, "invoice_id", "amount_cents")
	for _, p := range paid {
		p["paid_cents"] = store.AsInt(p, "amount_cents")
	}

	joined := store.LeftJoin(invoices, paid, "id", "invoice_id")
	ordered := store.OrderByString(joined, "issued_at", "id")

	rows := make([]model.ReportRow, 0, len(ordered))
	for _, row := range ordered {
		total := store.AsInt(row, "total_cents")
		paidCents := store.AsInt(row, "paid_cents")
		rows = append(rows, model.ReportRow{
			InvoiceID:  store.AsString(row, "id"),
			Customer:   store.AsString(row, "customer"),
			Status:     store.AsString(row, "status"),
			TotalCents: total,
			PaidCents:  paidCents,
			DueCents:   total - paidCents,
		})
	}
	return rows
}

// Sr is the per-status tally of a tenant's invoices.
type Sr struct {
	Status     string `json:"status"`
	Count      int    `json:"count"`
	TotalCents int    `json:"total_cents"`
}

// S groups a tenant's invoices by status, reporting how many invoices have each
// status and the sum of their totals. Only the tenant's own invoices are
// counted. Rows are ordered by status so the output is stable.
func (s *Rp) S(tenantID string) []Sr {
	invoices := store.Filter(s.db.Table(repository.TableInvoices).All(), func(row store.Row) bool {
		return store.AsString(row, "tenant_id") == tenantID
	})
	groups := store.GroupCountSum(invoices, "status", "total_cents")

	rows := make([]Sr, 0, len(groups))
	for _, g := range groups {
		rows = append(rows, Sr{Status: g.Key, Count: g.Count, TotalCents: g.Sum})
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].Status < rows[j].Status })
	return rows
}
