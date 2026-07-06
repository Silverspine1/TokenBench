use serde::{Deserialize, Serialize};

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
