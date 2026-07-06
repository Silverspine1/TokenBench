use crate::domain::Note;
use std::collections::HashMap;

/// An in-memory store of notes keyed by path. This models the persistence layer
/// without touching real disk, keeping the command surface deterministic and
/// testable offline.
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

    /// The revision currently stored at a path, or 0 when the path is unseen.
    pub fn current_revision(&self, path: &str) -> u64 {
        self.notes.get(path).map(|n| n.revision).unwrap_or(0)
    }

    pub fn get(&self, path: &str) -> Option<&Note> {
        self.notes.get(path)
    }

    /// Store content at a path with an explicit revision counter, replacing any
    /// prior note at that path.
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
