# Search Behavior

## Tokenization

`tokenize(text)` lowercases the input, splits on any non-alphanumeric boundary,
and drops empty tokens. Unicode alphanumerics are retained.

## Indexing

`SearchIndex` holds documents keyed by id. Supported operations:

- `add(id, title, path, content)` inserts or replaces a document.
- `update(id, content)` replaces content and re-derives tokens.
- `remove(id)` drops a document so it can no longer match.
- `rename(id, new_path)` changes the stored path only.
- `rescan(docs)` rebuilds the entire corpus from scratch.

## Querying

`query(q)` scores each document by the number of query-token occurrences in its
tokens and returns only documents with a positive score. Ordering is fully
deterministic: score descending, then id ascending. Removed documents never
appear; updated content and renamed paths are reflected immediately.
