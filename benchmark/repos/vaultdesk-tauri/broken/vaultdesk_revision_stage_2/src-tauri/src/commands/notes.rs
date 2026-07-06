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

/// Save a note, recording the content as a new revision. This baseline records
/// every save unconditionally and reports the new revision id.
pub fn save_note_with_revision(store: &mut RevisionStore, payload: SaveNotePayload) -> SaveResult {
    let rev = store.record(&payload.path, &payload.content);
    SaveResult {
        ok: true,
        revision: rev.revision_id,
        conflict: false,
        current_revision: rev.revision_id,
    }
}
