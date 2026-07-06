# Settings Migration

The current settings schema version is `2`.

## Reading

`get_settings(raw)` parses the JSON, runs `migrate`, and materializes a typed
`Settings { version, theme, vault_root, extra }`. The `extra` map carries every
field not named by the schema, so unknown keys survive a read.

## Migration rules

`migrate(value)` brings a document up to the current version:

- A document already at the current version is returned unchanged.
- Version 1 used a `darkMode` boolean. The migration derives `theme` from it
  when `theme` is absent (`true` -> `"dark"`, otherwise `"light"`), then removes
  the legacy `darkMode` key.
- A missing `vault_root` is filled with an empty string.
- Every unknown field is preserved verbatim.
