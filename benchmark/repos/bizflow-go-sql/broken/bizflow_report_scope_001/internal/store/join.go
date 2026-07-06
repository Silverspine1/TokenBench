package store

// merge produces a new row holding every column of left plus every column of
// right. When both sides define a column, the left value wins so a row's own
// identity columns are never overwritten by the joined side.
func merge(left, right Row) Row {
	out := make(Row, len(left)+len(right))
	for k, v := range right {
		out[k] = v
	}
	for k, v := range left {
		out[k] = v
	}
	return out
}

// index groups right rows by their join key for constant-time lookup.
func index(right []Row, rightKey string) map[string][]Row {
	m := make(map[string][]Row, len(right))
	for _, r := range right {
		k := AsString(r, rightKey)
		m[k] = append(m[k], r)
	}
	return m
}

// InnerJoin returns one merged row for every left/right pair whose join keys are
// equal. Left rows with no matching right row are dropped.
func InnerJoin(left, right []Row, leftKey, rightKey string) []Row {
	rightByKey := index(right, rightKey)
	out := []Row{}
	for _, l := range left {
		matches := rightByKey[AsString(l, leftKey)]
		for _, r := range matches {
			out = append(out, merge(l, r))
		}
	}
	return out
}

// LeftJoin returns every left row at least once. A left row with matching right
// rows yields one merged row per match; a left row with no match is still
// returned on its own, carrying only its own columns.
func LeftJoin(left, right []Row, leftKey, rightKey string) []Row {
	rightByKey := index(right, rightKey)
	out := []Row{}
	for _, l := range left {
		matches := rightByKey[AsString(l, leftKey)]
		for _, r := range matches {
			out = append(out, merge(l, r))
		}
	}
	return out
}
