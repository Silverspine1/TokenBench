use serde::{Deserialize, Serialize};

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
