use crate::fs::writer::{write_note, NoteStore};
use serde::{Deserialize, Serialize};

/// Payload for a revision-checked note save. `expected_revision` is the revision
/// the client believes is current; `overwrite` forces acceptance of a stale
/// save.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SaveNotePayload {
    pub path: String,
    pub content: String,
    pub expected_revision: u64,
    pub overwrite: bool,
}

/// Result of a save attempt. `conflict` is true exactly when a stale save was
/// rejected; in that case `current_revision` reports the stored revision and the
/// content is left unchanged.
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
///
/// - When the expected revision matches the stored revision, the content is
///   written and the revision is incremented.
/// - When the expected revision is stale and `overwrite` is false, the save is
///   rejected as a conflict and the stored content is left untouched.
/// - When the expected revision is stale and `overwrite` is true, the content is
///   written and the revision is incremented.
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
