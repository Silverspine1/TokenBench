package store

import "sort"

// Filter returns the rows for which keep reports true, preserving order.
func Filter(rows []Row, keep func(Row) bool) []Row {
	out := make([]Row, 0, len(rows))
	for _, r := range rows {
		if keep(r) {
			out = append(out, r)
		}
	}
	return out
}

// AsString returns the string value of a column, or "" when absent.
func AsString(r Row, col string) string {
	if v, ok := r[col]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

// AsInt returns the int value of a column, or 0 when absent.
func AsInt(r Row, col string) int {
	if v, ok := r[col]; ok {
		if n, ok := v.(int); ok {
			return n
		}
	}
	return 0
}

// OrderByString returns rows sorted by the named string columns in priority
// order. The sort is stable so equal keys keep their relative order.
func OrderByString(rows []Row, cols ...string) []Row {
	out := make([]Row, len(rows))
	copy(out, rows)
	sort.SliceStable(out, func(i, j int) bool {
		for _, c := range cols {
			a, b := AsString(out[i], c), AsString(out[j], c)
			if a != b {
				return a < b
			}
		}
		return false
	})
	return out
}

// GroupSum sums the value column for each distinct key column value. It returns
// one row per key with the key column and the summed value column.
func GroupSum(rows []Row, keyCol, valueCol string) []Row {
	order := []string{}
	totals := map[string]int{}
	for _, r := range rows {
		k := AsString(r, keyCol)
		if _, seen := totals[k]; !seen {
			order = append(order, k)
		}
		totals[k] += AsInt(r, valueCol)
	}
	out := make([]Row, 0, len(order))
	for _, k := range order {
		out = append(out, Row{keyCol: k, valueCol: totals[k]})
	}
	return out
}

// Group is the per-key tally produced by GroupCountSum.
type Group struct {
	Key   string
	Count int
	Sum   int
}

// GroupCountSum tallies rows by the key column. For each distinct key it reports
// how many rows carried that key and the sum of their value column. Groups are
// returned in first-seen key order.
func GroupCountSum(rows []Row, keyCol, valueCol string) []Group {
	idx := map[string]int{}
	out := []Group{}
	for _, r := range rows {
		k := AsString(r, keyCol)
		if i, ok := idx[k]; ok {
			out[i].Count++
			out[i].Sum += AsInt(r, valueCol)
		} else {
			idx[k] = len(out)
			out = append(out, Group{Key: k, Count: 1, Sum: AsInt(r, valueCol)})
		}
	}
	return out
}

// Page is one slice of a larger ordered result set.
type Page struct {
	Rows       []Row
	NextCursor int
	HasMore    bool
}

// Paginate returns at most limit rows starting at the given zero-based cursor.
// NextCursor points at the first row not yet returned; HasMore is true when more
// rows remain beyond this page.
func Paginate(rows []Row, cursor, limit int) Page {
	if cursor < 0 {
		cursor = 0
	}
	if limit <= 0 {
		return Page{Rows: []Row{}, NextCursor: cursor, HasMore: cursor < len(rows)}
	}
	end := cursor + limit
	if end > len(rows) {
		end = len(rows)
	}
	start := cursor
	if start > len(rows) {
		start = len(rows)
	}
	page := make([]Row, 0, end-start)
	page = append(page, rows[start:end]...)
	return Page{Rows: page, NextCursor: end, HasMore: end < len(rows)}
}
