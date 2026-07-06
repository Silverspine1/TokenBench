use crate::fs::revision_store::RevisionStore;
use serde::{Deserialize, Serialize};

/// Payload for a revision-checked note save. `expected_revision` is the revision
/// id the client believes is current; `overwrite` forces acceptance of a stale
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
/// rejected; in that case `current_revision` reports the stored revision id and
/// the content is left unchanged.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct SaveResult {
    pub ok: bool,
    pub revision: u64,
    pub conflict: bool,
    pub current_revision: u64,
}

/// Save a note using optimistic concurrency keyed on the note's revision
/// history. The latest recorded revision id is treated as the current revision.
///
/// - When the expected revision matches the current revision id, the content is
///   recorded as a new revision and the new revision id is returned.
/// - When the expected revision is stale and `overwrite` is false, the save is
///   rejected as a conflict; nothing is recorded and the stored content is left
///   untouched. `current_revision` reports the actual current revision id so the
///   caller can re-sync.
/// - When the expected revision is stale and `overwrite` is true, the content is
///   recorded as a new revision and the new revision id is returned.
pub fn save_note_with_revision(store: &mut RevisionStore, payload: SaveNotePayload) -> SaveResult {
    let current = store.current_revision_id(&payload.path);

    if payload.expected_revision != current && !payload.overwrite {
        return SaveResult {
            ok: false,
            revision: current,
            conflict: true,
            current_revision: current,
        };
    }

    let rev = store.record(&payload.path, &payload.content);
    SaveResult {
        ok: true,
        revision: rev.revision_id,
        conflict: false,
        current_revision: rev.revision_id,
    }
}
