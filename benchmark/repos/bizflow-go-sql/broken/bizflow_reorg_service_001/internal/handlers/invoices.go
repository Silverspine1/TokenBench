package handlers

import (
	"encoding/json"
	"errors"
	"net/http"

	"bizflow/internal/apiutil"
	"bizflow/internal/model"
	"bizflow/internal/legacy"
	"bizflow/internal/store"
)

// InvoiceHandler creates invoices.
type InvoiceHandler struct {
	invoices *legacy.InvoiceService
}

// NewInvoiceHandler wires an invoice handler to db.
func NewInvoiceHandler(db *store.DB) *InvoiceHandler {
	return &InvoiceHandler{invoices: legacy.NewInvoiceService(db)}
}

// createRequest is the JSON body accepted by POST /invoices.
type createRequest struct {
	TenantID string              `json:"tenant_id"`
	Customer string              `json:"customer"`
	IssuedAt string              `json:"issued_at"`
	Lines    []model.InvoiceLine `json:"lines"`
}

// ServeHTTP handles POST /invoices.
func (h *InvoiceHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		apiutil.WriteError(w, http.StatusMethodNotAllowed, "use POST")
		return
	}
	var req createRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		apiutil.WriteError(w, http.StatusBadRequest, "invalid JSON body")
		return
	}
	inv, err := h.invoices.Create(req.TenantID, req.Customer, req.IssuedAt, req.Lines)
	if err != nil {
		switch {
		case errors.Is(err, legacy.ErrInsufficientStock):
			apiutil.WriteError(w, http.StatusConflict, "insufficient stock")
		case errors.Is(err, legacy.ErrUnknownProduct):
			apiutil.WriteError(w, http.StatusBadRequest, "unknown product")
		case errors.Is(err, legacy.ErrEmptyInvoice):
			apiutil.WriteError(w, http.StatusBadRequest, "invoice has no lines")
		default:
			apiutil.WriteError(w, http.StatusInternalServerError, "could not create invoice")
		}
		return
	}
	apiutil.WriteJSON(w, http.StatusCreated, inv)
}
