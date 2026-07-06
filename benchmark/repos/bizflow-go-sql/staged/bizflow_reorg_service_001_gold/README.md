# bizflow

A small business back office service: invoices, inventory and tenant-scoped
revenue reports. It is a single Go module with an in-memory relational store, so
it builds and runs with the standard toolchain and no external database.

## Layout

```
cmd/bizflowd      runnable entry point: prints a tenant revenue report
internal/model    domain types (invoices, payments, products, report rows)
internal/store    in-memory relational store: filter, order, group, join, tx
internal/repository  table layout and queries
internal/service  business logic (invoice creation, inventory, reporting)
internal/handler  HTTP API
internal/bizdb    opens a migrated + seeded database
migrations        schema definition
fixtures          deterministic seed data
docs              behaviour notes
tests_visible     smoke tests (go test ./...)
```

## Running

```
go run ./cmd/bizflowd t_acme
```

## Tests

```
go test ./...
```
