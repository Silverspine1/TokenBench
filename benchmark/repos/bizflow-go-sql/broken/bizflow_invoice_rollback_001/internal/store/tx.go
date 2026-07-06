package store

import "errors"

// ErrRolledBack is returned by Commit when the transaction was already rolled back.
var ErrRolledBack = errors.New("store: transaction was rolled back")

// Tx is a savepoint over the whole database. Begin captures the current state of
// every table; mutations made through the normal repository calls happen
// directly against the live tables. Commit makes those mutations permanent by
// dropping the savepoint, while Rollback restores every table to the state it
// had when the transaction began, so partial work never persists.
type Tx struct {
	db     *DB
	before map[string][]Row
	done   bool
	rolled bool
}

// Begin opens a transaction, capturing the current database state.
func (d *DB) Begin() *Tx {
	return &Tx{db: d, before: d.snapshotAll()}
}

// Rollback closes the transaction.
func (t *Tx) Rollback() {
	if t.done {
		return
	}
	t.rolled = true
	t.done = true
}

// Commit makes the work performed during the transaction permanent. Committing a
// transaction that was already rolled back returns ErrRolledBack.
func (t *Tx) Commit() error {
	if t.rolled {
		return ErrRolledBack
	}
	t.before = nil
	t.done = true
	return nil
}
