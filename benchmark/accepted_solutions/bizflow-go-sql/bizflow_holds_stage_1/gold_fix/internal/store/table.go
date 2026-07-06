// Package store is a tiny in-memory relational store. It models tables of rows
// and the handful of relational operations the bizflow service needs: filtering,
// ordering, grouping, joins, cursor pagination and transactions. It is not a real
// SQL engine; it exists so the service can be exercised deterministically without
// any external database.
package store

import "sync"

// Row is a single record: column name to value.
type Row map[string]any

// clone makes an independent copy of a row so callers cannot mutate stored data.
func (r Row) clone() Row {
	out := make(Row, len(r))
	for k, v := range r {
		out[k] = v
	}
	return out
}

// Table is an ordered collection of rows with a known set of columns.
type Table struct {
	Name    string
	Columns []string
	rows    []Row
}

// Insert appends a copy of row to the table.
func (t *Table) Insert(r Row) {
	t.rows = append(t.rows, r.clone())
}

// All returns copies of every row, preserving insertion order.
func (t *Table) All() []Row {
	out := make([]Row, len(t.rows))
	for i, r := range t.rows {
		out[i] = r.clone()
	}
	return out
}

// Update rewrites every row matched by match through apply, in place. The
// mutator receives a private copy it may modify and return.
func (t *Table) Update(match func(Row) bool, apply func(Row) Row) {
	for i, r := range t.rows {
		if match(r) {
			t.rows[i] = apply(r.clone())
		}
	}
}

// Delete removes every row matched by match, preserving the order of the rest.
func (t *Table) Delete(match func(Row) bool) {
	kept := t.rows[:0]
	for _, r := range t.rows {
		if !match(r) {
			kept = append(kept, r)
		}
	}
	t.rows = kept
}

// Len reports how many rows the table holds.
func (t *Table) Len() int { return len(t.rows) }

// snapshot returns a deep copy of the table's rows.
func (t *Table) snapshot() []Row {
	out := make([]Row, len(t.rows))
	for i, r := range t.rows {
		out[i] = r.clone()
	}
	return out
}

// restore replaces the table's rows with a previously taken snapshot.
func (t *Table) restore(rows []Row) {
	t.rows = make([]Row, len(rows))
	for i, r := range rows {
		t.rows[i] = r.clone()
	}
}

// DB is a named set of tables guarded by a mutex.
type DB struct {
	mu     sync.Mutex
	tables map[string]*Table
}

// NewDB returns an empty database.
func NewDB() *DB {
	return &DB{tables: make(map[string]*Table)}
}

// CreateTable registers a new empty table. An existing table is left untouched.
func (d *DB) CreateTable(name string, columns ...string) *Table {
	d.mu.Lock()
	defer d.mu.Unlock()
	if t, ok := d.tables[name]; ok {
		return t
	}
	t := &Table{Name: name, Columns: columns}
	d.tables[name] = t
	return t
}

// Table returns the named table, or nil if it has not been created.
func (d *DB) Table(name string) *Table {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.tables[name]
}

// Has reports whether a table with the given name exists.
func (d *DB) Has(name string) bool {
	d.mu.Lock()
	defer d.mu.Unlock()
	_, ok := d.tables[name]
	return ok
}

// snapshotAll captures the rows of every table.
func (d *DB) snapshotAll() map[string][]Row {
	d.mu.Lock()
	defer d.mu.Unlock()
	snap := make(map[string][]Row, len(d.tables))
	for name, t := range d.tables {
		snap[name] = t.snapshot()
	}
	return snap
}

// restoreAll resets every captured table to its snapshot.
func (d *DB) restoreAll(snap map[string][]Row) {
	d.mu.Lock()
	defer d.mu.Unlock()
	for name, rows := range snap {
		if t, ok := d.tables[name]; ok {
			t.restore(rows)
		}
	}
}
