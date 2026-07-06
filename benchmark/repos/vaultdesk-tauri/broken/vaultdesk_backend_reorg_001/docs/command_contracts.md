# Command Contracts

The backend exposes a small set of commands as plain functions. Each returns a
serde-serializable value, and failures return the normalized `AppError` shape
`{ code, message }`.

## open_file(vault_root, requested) -> FileEntry | AppError

Resolves `requested` against `vault_root` using the vault boundary rules, then
returns a `FileEntry { path, name, size }`. A path that escapes the vault yields
`AppError { code: "PATH_ESCAPE", ... }`.

## search(index, q) -> SearchResult[]

Runs the query against the in-memory index and returns ranked results. Each
`SearchResult` serializes to `{ id, title, path, snippet, score }`. Ordering is
score descending, then id ascending.

## get_settings(raw) -> Settings | AppError

Parses the raw JSON, migrates it to the current schema version while preserving
unknown fields, and returns the typed `Settings`. Unparseable input yields
`AppError { code: "INVALID_INPUT", ... }`.

## save_note_with_revision(store, payload) -> SaveResult

Optimistic concurrency keyed on an explicit revision counter. The payload
serializes with camelCase keys: `path`, `content`, `expectedRevision`,
`overwrite`. The result serializes with camelCase keys: `ok`, `revision`,
`conflict`, `currentRevision`.
