package handler

import (
	"net/http"

	"bizflow/internal/store"
)

// NewRouter builds the HTTP routes for the bizflow API.
func NewRouter(db *store.DB) *http.ServeMux {
	mux := http.NewServeMux()
	mux.Handle("/reports/revenue", NewReportHandler(db))
	mux.Handle("/invoices", NewInvoiceHandler(db))
	return mux
}
