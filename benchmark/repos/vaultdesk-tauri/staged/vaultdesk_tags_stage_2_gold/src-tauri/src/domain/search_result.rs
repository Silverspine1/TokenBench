use serde::{Deserialize, Serialize};

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
