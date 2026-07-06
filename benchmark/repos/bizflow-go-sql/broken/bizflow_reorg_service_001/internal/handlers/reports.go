// Package handlers exposes the bizflow services over a small HTTP API.
package handlers

import (
	"net/http"

	"bizflow/internal/apiutil"
	"bizflow/internal/legacy"
	"bizflow/internal/store"
)

// ReportHandler serves tenant revenue reports.
type ReportHandler struct {
	reports *legacy.ReportService
}

// NewReportHandler wires a report handler to db.
func NewReportHandler(db *store.DB) *ReportHandler {
	return &ReportHandler{reports: legacy.NewReportService(db)}
}

// ServeHTTP handles GET /reports/revenue?tenant=<id>.
func (h *ReportHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	tenant := r.URL.Query().Get("tenant")
	if tenant == "" {
		apiutil.WriteError(w, http.StatusBadRequest, "missing tenant")
		return
	}
	apiutil.WriteJSON(w, http.StatusOK, h.reports.TenantReport(tenant))
}
