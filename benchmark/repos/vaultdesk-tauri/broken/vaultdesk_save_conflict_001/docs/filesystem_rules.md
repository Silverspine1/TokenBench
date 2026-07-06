# Filesystem Rules

All file access is mediated by `resolve_in_vault(vault_root, requested)`, which
returns a forward-slash normalized path guaranteed to live inside the vault.

## Normalization

- Both `/` and `\` are accepted as separators and normalized to `/`.
- Empty segments and `.` segments are dropped.
- A `..` segment pops the preceding segment.

## Boundary enforcement

- A relative `requested` path is appended onto the vault root.
- An absolute `requested` path is matched directly against the root segments.
- Containment is decided segment by segment, never by raw string prefix. This
  is why a sibling directory whose name merely shares a prefix with the vault
  (for example `/vault/data-evil` against root `/vault/data`) is rejected, while
  a genuine nested file such as `notes/sub/a.md` is accepted.
- Any path that climbs above the root resolves to
  `AppError { code: "PATH_ESCAPE", ... }`.

## Notes persistence

Notes are held in an in-memory `NoteStore` keyed by path. Each note carries an
explicit integer `revision` counter; revisions are never derived from a clock.
