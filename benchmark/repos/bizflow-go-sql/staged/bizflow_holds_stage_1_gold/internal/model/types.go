// Package model holds the domain types shared across the bizflow service.
package model

// Tenant is a single business account. All data is scoped to one tenant.
type Tenant struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

// Product is an inventory item owned by a tenant.
type Product struct {
	TenantID string `json:"tenant_id"`
	SKU      string `json:"sku"`
	Name     string `json:"name"`
	OnHand   int    `json:"on_hand"`
	Reserved int    `json:"reserved"`
}

// Available stock is what is on hand minus what is already reserved.
func (p Product) Available() int { return p.OnHand - p.Reserved }

// InvoiceLine is one billed item on an invoice.
type InvoiceLine struct {
	SKU        string `json:"sku"`
	Quantity   int    `json:"quantity"`
	UnitCents  int    `json:"unit_cents"`
}

// LineTotal is the extended price for the line in cents.
func (l InvoiceLine) LineTotal() int { return l.Quantity * l.UnitCents }

// Invoice is a customer bill. Status is one of open, paid, void.
type Invoice struct {
	ID         string        `json:"id"`
	TenantID   string        `json:"tenant_id"`
	Customer   string        `json:"customer"`
	Status     string        `json:"status"`
	IssuedAt   string        `json:"issued_at"`
	Lines      []InvoiceLine `json:"lines"`
}

// Total is the sum of all line totals in cents.
func (i Invoice) Total() int {
	sum := 0
	for _, l := range i.Lines {
		sum += l.LineTotal()
	}
	return sum
}

// Payment is money received against an invoice.
type Payment struct {
	ID        string `json:"id"`
	InvoiceID string `json:"invoice_id"`
	TenantID  string `json:"tenant_id"`
	AmountCents int  `json:"amount_cents"`
	PaidAt    string `json:"paid_at"`
}

// Hold is a temporary reservation of stock for a tenant that is not yet tied to
// an invoice. While a hold is live it ties up Quantity units of the product, so
// that stock is not available to anyone else.
type Hold struct {
	ID        string `json:"id"`
	TenantID  string `json:"tenant_id"`
	SKU       string `json:"sku"`
	Quantity  int    `json:"quantity"`
	CreatedAt string `json:"created_at"`
}

// ReportRow is one line of a tenant revenue report.
type ReportRow struct {
	InvoiceID  string `json:"invoice_id"`
	Customer   string `json:"customer"`
	Status     string `json:"status"`
	TotalCents int    `json:"total_cents"`
	PaidCents  int    `json:"paid_cents"`
	DueCents   int    `json:"due_cents"`
}
