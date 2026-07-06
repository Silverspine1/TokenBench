package service

import (
	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/store"
)

// ReportService exposes tenant revenue reporting to the handlers.
type ReportService struct {
	reports *repository.ReportRepo
}

// NewReportService wires a report service to db.
func NewReportService(db *store.DB) *ReportService {
	return &ReportService{reports: repository.NewReportRepo(db)}
}

// TenantSummary is the headline view of a tenant's revenue.
type TenantSummary struct {
	TenantID   string            `json:"tenant_id"`
	Rows       []model.ReportRow `json:"rows"`
	TotalCents int               `json:"total_cents"`
	PaidCents  int               `json:"paid_cents"`
	DueCents   int               `json:"due_cents"`
}

// TenantReport returns every report row for the tenant plus the rolled-up totals.
func (s *ReportService) TenantReport(tenantID string) TenantSummary {
	rows := s.reports.TenantRevenue(tenantID)
	total, paid, due := s.reports.TenantTotals(tenantID)
	return TenantSummary{
		TenantID:   tenantID,
		Rows:       rows,
		TotalCents: total,
		PaidCents:  paid,
		DueCents:   due,
	}
}
