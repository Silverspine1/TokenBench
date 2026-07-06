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
            doc.tokens = tokenize(content);
        }
    }

    /// Drop a document so it can no longer appear in any query.
    pub fn remove(&mut self, id: &str) {
        self.docs.remove(id);
    }

    /// Change the stored path of an existing document. Absent ids are ignored.
    pub fn rename(&mut self, id: &str, new_path: &str) {
        if let Some(doc) = self.docs.get_mut(id) {
            doc.path = new_path.to_string();
        }
    }

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
        self.collect(&query_tokens, None)
    }

    /// Composable query: text tokens and an optional id allowlist combine into a
    /// single ranked result set.
    ///
    /// - When `allowed` is `None`, every document is eligible (plain text search).
    /// - When `allowed` is `Some(set)`, only documents whose id is in the set are
    ///   eligible (e.g. a tag filter).
    /// - When the text is empty, eligible documents are returned with a uniform
    ///   score so a tag-only filter still yields a deterministic, ordered list.
    ///
    /// This is the single search primitive every higher-level path composes with,
    /// so text-only, tag-only, and combined queries share one ranking and one
    /// ordering rule (score descending, then id ascending).
    pub fn query_filtered(&self, q: &str, allowed: Option<&[String]>) -> Vec<SearchResult> {
        let query_tokens = tokenize(q);
        let allow_set: Option<std::collections::BTreeSet<&str>> =
            allowed.map(|ids| ids.iter().map(|s| s.as_str()).collect());
        self.collect_filtered(&query_tokens, allow_set.as_ref())
    }

    fn collect(&self, query_tokens: &[String], allowed: Option<&[String]>) -> Vec<SearchResult> {
        let allow_set: Option<std::collections::BTreeSet<&str>> =
            allowed.map(|ids| ids.iter().map(|s| s.as_str()).collect());
        self.collect_filtered(query_tokens, allow_set.as_ref())
    }

    fn collect_filtered(
        &self,
        query_tokens: &[String],
        allowed: Option<&std::collections::BTreeSet<&str>>,
    ) -> Vec<SearchResult> {
        let text_empty = query_tokens.is_empty();
        // A tag-only filter (no text, no allowlist) has nothing to constrain on
        // and matches nothing, mirroring an empty text query.
        if text_empty && allowed.is_none() {
            return Vec::new();
        }

        let mut hits: Vec<SearchResult> = Vec::new();
        for doc in self.docs.values() {
            if let Some(set) = allowed {
                if !set.contains(doc.id.as_str()) {
                    continue;
                }
            }
            let score: f64 = if text_empty {
                // Tag-only path: uniform score so ordering falls back to id asc.
                1.0
            } else {
                let mut s = 0.0;
                for qt in query_tokens {
                    for dt in &doc.tokens {
                        if dt == qt {
                            s += 1.0;
                        }
                    }
                }
                s
            };
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
