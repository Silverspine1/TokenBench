//! Backend file-handling pile. Path resolution, directory listing, the note
//! store, and the file/note command entrypoints were all folded together here
//! during an earlier migration, so anything that touches a path or a stored note
//! ends up in this file.

use crate::blob::{FileEntry, Note};
use crate::errors::AppError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// path handling
// ---------------------------------------------------------------------------

/// Whether a path string begins with a leading separator, marking it as
/// absolute rather than vault-relative.
fn is_absolute(input: &str) -> bool {
    input.starts_with('/') || input.starts_with('\\')
}

/// Split a path on both separators and collapse `.` and `..` segments. A `..`
/// that would climb above the first segment is reported by returning an error.
fn normalize_segments(input: &str) -> Result<Vec<String>, AppError> {
    let mut out: Vec<String> = Vec::new();
    for raw in input.split(['/', '\\']) {
        match raw {
            "" | "." => continue,
            ".." => {
                if out.pop().is_none() {
                    return Err(AppError::path_escape(
                        "requested path climbs above the vault root",
                    ));
                }
            }
            other => out.push(other.to_string()),
        }
    }
    Ok(out)
}

/// Resolve a requested path against a vault root, returning a forward-slash
/// normalized canonical path guaranteed to live inside the vault.
pub fn resolve_in_vault(vault_root: &str, requested: &str) -> Result<String, AppError> {
    let root_segments = normalize_segments(vault_root)?;
    let requested_segments = normalize_segments(requested)?;

    let combined: Vec<String> = if is_absolute(requested) {
        requested_segments
    } else {
        let mut c = root_segments.clone();
        c.extend(requested_segments);
        c
    };

    if combined.len() < root_segments.len() {
        return Err(AppError::path_escape("requested path escapes the vault"));
    }
    for (i, seg) in root_segments.iter().enumerate() {
        if &combined[i] != seg {
            return Err(AppError::path_escape("requested path escapes the vault"));
        }
    }

    Ok(combined.join("/"))
}

// ---------------------------------------------------------------------------
// listing
// ---------------------------------------------------------------------------

/// Return the entries sorted deterministically by path. The input slice is left
/// untouched; a new owned vector is produced.
pub fn scan(entries: &[FileEntry]) -> Vec<FileEntry> {
    let mut out = entries.to_vec();
    out.sort_by(|a, b| a.path.cmp(&b.path));
    out
}

// ---------------------------------------------------------------------------
// note storage
// ---------------------------------------------------------------------------

/// An in-memory store of notes keyed by path.
#[derive(Debug, Default, Clone)]
pub struct NoteStore {
    notes: HashMap<String, Note>,
}

impl NoteStore {
    pub fn new() -> Self {
        NoteStore {
            notes: HashMap::new(),
        }
    }

    pub fn current_revision(&self, path: &str) -> u64 {
        self.notes.get(path).map(|n| n.revision).unwrap_or(0)
    }

    pub fn get(&self, path: &str) -> Option<&Note> {
        self.notes.get(path)
    }

    pub fn put(&mut self, path: &str, content: &str, revision: u64) -> Note {
        let note = Note::new(path, content, revision);
        self.notes.insert(path.to_string(), note.clone());
        note
    }
}

/// Write a note into the store at the given revision and return the stored note.
pub fn write_note(store: &mut NoteStore, path: &str, content: &str, revision: u64) -> Note {
    store.put(path, content, revision)
}

// ---------------------------------------------------------------------------
// commands: file + note
// ---------------------------------------------------------------------------

/// Resolve and describe a file inside the vault.
pub fn open_file(vault_root: &str, requested: &str) -> Result<FileEntry, AppError> {
    let resolved = resolve_in_vault(vault_root, requested)?;
    let name = resolved
        .rsplit('/')
        .next()
        .unwrap_or(&resolved)
        .to_string();
    Ok(FileEntry::new(&resolved, &name, 0))
}

/// Payload for a revision-checked note save.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SaveNotePayload {
    pub path: String,
    pub content: String,
    pub expected_revision: u64,
    pub overwrite: bool,
}

/// Result of a save attempt.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SaveResult {
    pub ok: bool,
    pub revision: u64,
    pub conflict: bool,
    pub current_revision: u64,
}

/// Save a note using optimistic concurrency keyed on an explicit revision
/// counter.
pub fn save_note_with_revision(store: &mut NoteStore, payload: SaveNotePayload) -> SaveResult {
    let current = store.current_revision(&payload.path);

    if payload.expected_revision == current {
        let next = current + 1;
        write_note(store, &payload.path, &payload.content, next);
        return SaveResult {
            ok: true,
            revision: next,
            conflict: false,
            current_revision: next,
        };
    }

    if !payload.overwrite {
        return SaveResult {
            ok: false,
            revision: current,
            conflict: true,
            current_revision: current,
        };
    }

    let next = current + 1;
    write_note(store, &payload.path, &payload.content, next);
    SaveResult {
        ok: true,
        revision: next,
        conflict: false,
        current_revision: next,
    }
}
