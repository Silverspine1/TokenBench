use std::collections::{BTreeMap, BTreeSet};

/// An in-memory store of tags and their note assignments. Tag names are the
/// keys; each tag holds the set of note ids it is assigned to. Both the tag set
/// and the per-tag id set are ordered, so every read is deterministic and free
/// of clock or hash-iteration dependence.
///
/// The store is deliberately a standalone primitive: it knows nothing about the
/// text index. Composition of text and tag filters happens one layer up, in the
/// search path, so new query shapes can be added without changing this type.
#[derive(Debug, Default, Clone)]
pub struct TagStore {
    tags: BTreeMap<String, BTreeSet<String>>,
}

impl TagStore {
    pub fn new() -> Self {
        TagStore {
            tags: BTreeMap::new(),
        }
    }

    /// Create a tag if it does not already exist. Creating an existing tag is a
    /// no-op that preserves its assignments. Returns true when the tag exists
    /// after the call (always true unless the name is empty).
    pub fn create_tag(&mut self, name: &str) -> bool {
        if name.is_empty() {
            return false;
        }
        self.tags.entry(name.to_string()).or_default();
        true
    }

    pub fn has_tag(&self, name: &str) -> bool {
        self.tags.contains_key(name)
    }

    /// Assign a tag to a note. The tag is created on demand. Assigning the same
    /// (tag, note) pair more than once is idempotent: the second call changes
    /// nothing and still reports success. Returns true on success.
    pub fn assign(&mut self, name: &str, note_id: &str) -> bool {
        if name.is_empty() || note_id.is_empty() {
            return false;
        }
        self.tags
            .entry(name.to_string())
            .or_default()
            .insert(note_id.to_string());
        true
    }

    /// Remove a tag from a note. Removing a pair that is not present is a no-op
    /// that still reports success. The tag itself is retained even when its last
    /// assignment is removed, so a later assign reuses it.
    pub fn remove(&mut self, name: &str, note_id: &str) -> bool {
        if let Some(ids) = self.tags.get_mut(name) {
            ids.remove(note_id);
        }
        true
    }

    /// The note ids carrying a tag, in ascending id order. An unknown tag yields
    /// an empty list.
    pub fn notes_with_tag(&self, name: &str) -> Vec<String> {
        self.tags
            .get(name)
            .map(|ids| ids.iter().cloned().collect())
            .unwrap_or_default()
    }

    /// True when a note carries a tag.
    pub fn note_has_tag(&self, name: &str, note_id: &str) -> bool {
        self.tags
            .get(name)
            .map(|ids| ids.contains(note_id))
            .unwrap_or(false)
    }

    /// All tag names in ascending order.
    pub fn tag_names(&self) -> Vec<String> {
        self.tags.keys().cloned().collect()
    }
}
