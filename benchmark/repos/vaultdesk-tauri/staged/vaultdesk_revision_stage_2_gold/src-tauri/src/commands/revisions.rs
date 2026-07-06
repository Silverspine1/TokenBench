use crate::domain::revision::Revision;
use crate::fs::revision_store::RevisionStore;

/// Record the current `content` of the note at `path` as a new revision and
/// return the stored revision (including its freshly assigned monotonic
/// `revision_id`). Saving a note's content always preserves the prior versions
/// so users can inspect history later.
pub fn save_note_revision(store: &mut RevisionStore, path: &str, content: &str) -> Revision {
    store.record(path, content)
}

/// List every recorded revision for the note at `path`, oldest first. The order
/// is deterministic: revisions are returned in the order they were recorded,
/// which is also strictly ascending by `revision_id`.
pub fn list_note_revisions(store: &RevisionStore, path: &str) -> Vec<Revision> {
    store.list(path).to_vec()
}

/// Fetch a specific past revision of the note at `path` by its `revision_id`,
/// or `None` when no revision with that id exists.
pub fn get_note_revision(
    store: &RevisionStore,
    path: &str,
    revision_id: u64,
) -> Option<Revision> {
    store.get(path, revision_id).cloned()
}
