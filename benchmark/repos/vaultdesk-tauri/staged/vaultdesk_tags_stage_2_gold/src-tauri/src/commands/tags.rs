use crate::domain::SearchResult;
use crate::index::{SearchIndex, TagStore};

/// Create a tag. Returns true when the tag exists after the call. Creating a tag
/// that already exists is a no-op and still reports success.
pub fn create_tag(tags: &mut TagStore, name: &str) -> bool {
    tags.create_tag(name)
}

/// Assign a tag to a note. The tag is created on demand and a repeated
/// assignment of the same pair is idempotent.
pub fn assign_tag_to_note(tags: &mut TagStore, name: &str, note_id: &str) -> bool {
    tags.assign(name, note_id)
}

/// Remove a tag from a note. Removing a pair that is not present is a no-op that
/// still reports success.
pub fn remove_tag_from_note(tags: &mut TagStore, name: &str, note_id: &str) -> bool {
    tags.remove(name, note_id)
}

/// Search notes carrying a tag. Implemented as a tag-only filter over the shared
/// search primitive, so the returned shape and ordering match plain text search.
pub fn search_by_tag(index: &SearchIndex, tags: &TagStore, name: &str) -> Vec<SearchResult> {
    let ids = tags.notes_with_tag(name);
    index.query_filtered("", Some(&ids))
}
