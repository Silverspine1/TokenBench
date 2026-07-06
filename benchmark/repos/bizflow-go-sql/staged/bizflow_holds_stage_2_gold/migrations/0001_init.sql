-- 0001_init: base schema for the bizflow service.

CREATE TABLE tenants (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE products (
    tenant_id TEXT NOT NULL,
    sku       TEXT NOT NULL,
    name      TEXT NOT NULL,
    on_hand   INTEGER NOT NULL DEFAULT 0,
    reserved  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, sku)
);

CREATE TABLE invoices (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    customer    TEXT NOT NULL,
    status      TEXT NOT NULL,
    issued_at   TEXT NOT NULL,
    total_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE payments (
    id           TEXT PRIMARY KEY,
    invoice_id   TEXT NOT NULL,
    tenant_id    TEXT NOT NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    paid_at      TEXT NOT NULL
);
