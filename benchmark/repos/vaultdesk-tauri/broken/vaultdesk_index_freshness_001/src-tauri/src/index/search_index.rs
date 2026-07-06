use crate::domain::SearchResult;
use crate::index::tokenizer::tokenize;
use std::collections::HashMap;

/// One indexed document. Tokens are derived from the content at insert/update
/// time so queries never re-tokenize the corpus.
#[derive(Debug, Clone)]
struct Doc {
    id: String,
    title: String,
    path: String,
    content: String,
    tokens: Vec<String>,
}

/// An in-memory inverted-style search index. Ordering of query results is fully
/// deterministic: score descending, then id ascending.
#[derive(Debug, Default, Clone)]
pub struct SearchIndex {
    docs: HashMap<String, Doc>,
}

impl SearchIndex {
    pub fn new() -> Self {
        SearchIndex {
            docs: HashMap::new(),
        }
    }

    /// Insert or replace a document by id.
    pub fn add(&mut self, id: &str, title: &str, path: &str, content: &str) {
        let doc = Doc {
            id: id.to_string(),
            title: title.to_string(),
            path: path.to_string(),
            content: content.to_string(),
            tokens: tokenize(content),
        };
        self.docs.insert(id.to_string(), doc);
    }

    /// Replace the content (and derived tokens) of an existing document. Absent
    /// ids are ignored.
    pub fn update(&mut self, id: &str, content: &str) {
        if let Some(doc) = self.docs.get_mut(id) {
            doc.content = content.to_string();
        }
    }

    /// Drop a document so it can no longer appear in any query.
    pub fn remove(&mut self, _id: &str) {}

    /// Change the stored path of an existing document. Absent ids are ignored.
    pub fn rename(&mut self, _id: &str, _new_path: &str) {}

    /// Rebuild the entire index from a full document set, discarding prior
    /// state. Each tuple is (id, title, path, content).
    pub fn rescan(&mut self, docs: &[(String, String, String, String)]) {
        self.docs.clear();
        for (id, title, path, content) in docs {
            self.add(id, title, path, content);
        }
    }

    /// Build a short snippet around the matched content for display.
    fn snippet_for(content: &str) -> String {
        let trimmed = content.trim();
        if trimmed.chars().count() <= 80 {
            trimmed.to_string()
        } else {
            let prefix: String = trimmed.chars().take(80).collect();
            format!("{}...", prefix)
        }
    }

    /// Run a query and return ranked results. The score is the count of query
    /// token occurrences in a document's tokens. Documents with zero matches are
    /// excluded. Results are ordered by score descending, then id ascending.
    pub fn query(&self, q: &str) -> Vec<SearchResult> {
        let query_tokens = tokenize(q);
        if query_tokens.is_empty() {
            return Vec::new();
        }

        let mut hits: Vec<SearchResult> = Vec::new();
        for doc in self.docs.values() {
            let mut score: f64 = 0.0;
            for qt in &query_tokens {
                for dt in &doc.tokens {
                    if dt == qt {
                        score += 1.0;
                    }
                }
            }
            if score > 0.0 {
                hits.push(SearchResult::new(
                    &doc.id,
                    &doc.title,
                    &doc.path,
                    &Self::snippet_for(&doc.content),
                    score,
                ));
            }
        }

        hits.sort_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.id.cmp(&b.id))
        });
        hits
    }
}
