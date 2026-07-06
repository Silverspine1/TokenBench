-- 0002_indexes: lookup indexes for tenant-scoped reporting.

CREATE INDEX idx_invoices_tenant ON invoices (tenant_id);
CREATE INDEX idx_payments_tenant ON payments (tenant_id);
CREATE INDEX idx_payments_invoice ON payments (invoice_id);
CREATE INDEX idx_products_tenant ON products (tenant_id);
