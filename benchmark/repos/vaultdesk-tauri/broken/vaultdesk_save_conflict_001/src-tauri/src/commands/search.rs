use crate::domain::SearchResult;
use crate::index::SearchIndex;

/// Run a search query against the index and return ranked results.
pub fn search(index: &SearchIndex, q: &str) -> Vec<SearchResult> {
    index.query(q)
}
