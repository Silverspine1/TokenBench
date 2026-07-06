use serde::{Deserialize, Serialize};

/// Stable per-note metadata captured alongside a stored revision. The metadata
/// is derived purely from the content, never from a wall clock, so revisions are
/// fully deterministic and reproducible offline.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct RevisionMeta {
    /// Length of the content in bytes at the time the revision was recorded.
    pub byte_len: u64,
    /// Number of lines in the content (newline-separated, trailing newline
    /// counted as terminating the final line).
    pub line_count: u64,
}

impl RevisionMeta {
    pub fn of(content: &str) -> Self {
        let byte_len = content.len() as u64;
        let line_count = if content.is_empty() {
            0
        } else {
            content.lines().count() as u64
        };
        RevisionMeta {
            byte_len,
            line_count,
        }
    }
}

/// A single addressable version of a note's content. `revision_id` is a stable,
/// monotonically increasing counter assigned when the revision is recorded; it
/// is never reused and never derived from a timestamp.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct Revision {
    pub revision_id: u64,
    pub content: String,
    pub meta: RevisionMeta,
}

impl Revision {
    pub fn new(revision_id: u64, content: &str) -> Self {
        Revision {
            revision_id,
            content: content.to_string(),
            meta: RevisionMeta::of(content),
        }
    }
}
