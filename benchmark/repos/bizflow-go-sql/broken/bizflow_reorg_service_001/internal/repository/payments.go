package repository

import (
	"bizflow/internal/model"
	"bizflow/internal/store"
)

// PaymentRepo reads and writes payment rows.
type PaymentRepo struct {
	db *store.DB
}

// NewPaymentRepo returns a repository bound to db, ensuring the table exists.
func NewPaymentRepo(db *store.DB) *PaymentRepo {
	db.CreateTable(TablePayments, "id", "invoice_id", "tenant_id", "amount_cents", "paid_at")
	return &PaymentRepo{db: db}
}

// Insert stores one payment.
func (r *PaymentRepo) Insert(p model.Payment) {
	r.db.Table(TablePayments).Insert(store.Row{
		"id":           p.ID,
		"invoice_id":   p.InvoiceID,
		"tenant_id":    p.TenantID,
		"amount_cents": p.AmountCents,
		"paid_at":      p.PaidAt,
	})
}
