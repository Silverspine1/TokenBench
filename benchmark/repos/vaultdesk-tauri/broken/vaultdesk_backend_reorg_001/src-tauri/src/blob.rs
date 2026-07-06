//! Shared value types used across the backend. A previous consolidation pass
//! grouped every serde-facing struct into this single file so the wire shapes
//! stay in one place. The entries, notes, ranked hits, and settings record all
//! live here together.

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

/// The settings schema version this build reads and writes.
pub const CURRENT_SETTINGS_VERSION: u32 = 2;

/// A single entry in a vault listing.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FileEntry {
    pub path: String,
    pub name: String,
    pub size: u64,
}

impl FileEntry {
    pub fn new(path: &str, name: &str, size: u64) -> Self {
        FileEntry {
            path: path.to_string(),
            name: name.to_string(),
            size,
        }
    }
}

/// A stored note with a monotonically increasing revision counter. The
/// revision is an explicit integer, never derived from a clock.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Note {
    pub path: String,
    pub content: String,
    pub revision: u64,
}

impl Note {
    pub fn new(path: &str, content: &str, revision: u64) -> Self {
        Note {
            path: path.to_string(),
            content: content.to_string(),
            revision,
        }
    }
}

/// A ranked hit returned by the search index. Field names serialize exactly to
/// id, title, path, snippet, score.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SearchResult {
    pub id: String,
    pub title: String,
    pub path: String,
    pub snippet: String,
    pub score: f64,
}

impl SearchResult {
    pub fn new(id: &str, title: &str, path: &str, snippet: &str, score: f64) -> Self {
        SearchResult {
            id: id.to_string(),
            title: title.to_string(),
            path: path.to_string(),
            snippet: snippet.to_string(),
            score,
        }
    }
}

/// User settings. Unknown fields are preserved verbatim through load and
/// migration so that newer keys written by a future build are not discarded.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Settings {
    pub version: u32,
    #[serde(default)]
    pub theme: String,
    #[serde(default)]
    pub vault_root: String,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            version: CURRENT_SETTINGS_VERSION,
            theme: "light".to_string(),
            vault_root: String::new(),
            extra: Map::new(),
        }
    }
}
