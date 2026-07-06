//! Backend query-and-config pile. Tokenization, the in-memory index, the search
//! command, and the whole settings load/migrate path were merged into this file
//! during the same migration that produced core1. Anything that answers a query
//! or reads configuration lives here.

use crate::blob::{SearchResult, Settings, CURRENT_SETTINGS_VERSION};
use crate::errors::AppError;
use serde_json::{Map, Value};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// tokenization
// ---------------------------------------------------------------------------

/// Split text into lowercase tokens on any non-alphanumeric boundary, dropping
/// empty tokens. Unicode alphanumerics are retained.
pub fn tokenize(text: &str) -> Vec<String> {
    text.split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(|s| s.to_lowercase())
        .collect()
}

// ---------------------------------------------------------------------------
// index
// ---------------------------------------------------------------------------

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

    pub fn update(&mut self, id: &str, content: &str) {
        if let Some(doc) = self.docs.get_mut(id) {
            doc.content = content.to_string();
            doc.tokens = tokenize(content);
        }
    }

    pub fn remove(&mut self, id: &str) {
        self.docs.remove(id);
    }

    pub fn rename(&mut self, id: &str, new_path: &str) {
        if let Some(doc) = self.docs.get_mut(id) {
            doc.path = new_path.to_string();
        }
    }

    pub fn rescan(&mut self, docs: &[(String, String, String, String)]) {
        self.docs.clear();
        for (id, title, path, content) in docs {
            self.add(id, title, path, content);
        }
    }

    fn snippet_for(content: &str) -> String {
        let trimmed = content.trim();
        if trimmed.chars().count() <= 80 {
            trimmed.to_string()
        } else {
            let prefix: String = trimmed.chars().take(80).collect();
            format!("{}...", prefix)
        }
    }

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

// ---------------------------------------------------------------------------
// command: search
// ---------------------------------------------------------------------------

/// Run a search query against the index and return ranked results.
pub fn search(index: &SearchIndex, q: &str) -> Vec<SearchResult> {
    index.query(q)
}

// ---------------------------------------------------------------------------
// settings load + migrate
// ---------------------------------------------------------------------------

/// Parse a raw JSON string into a Settings value.
pub fn load_settings(raw: &str) -> Result<Settings, AppError> {
    serde_json::from_str::<Settings>(raw)
        .map_err(|e| AppError::invalid_input(&format!("could not parse settings: {}", e)))
}

/// Migrate a settings document up to the current schema version while
/// preserving every unknown field.
pub fn migrate(value: Value) -> Value {
    let mut obj: Map<String, Value> = match value {
        Value::Object(m) => m,
        other => return other,
    };

    let version = obj
        .get("version")
        .and_then(|v| v.as_u64())
        .unwrap_or(1) as u32;

    if version >= CURRENT_SETTINGS_VERSION {
        return Value::Object(obj);
    }

    if !obj.contains_key("theme") {
        let dark = obj
            .get("darkMode")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let theme = if dark { "dark" } else { "light" };
        obj.insert("theme".to_string(), Value::String(theme.to_string()));
    }
    obj.remove("darkMode");

    if !obj.contains_key("vault_root") {
        obj.insert("vault_root".to_string(), Value::String(String::new()));
    }

    obj.insert("version".to_string(), Value::from(CURRENT_SETTINGS_VERSION));

    Value::Object(obj)
}

/// Read settings for the frontend: parse the raw JSON, migrate it up to the
/// current schema version while preserving unknown fields, then materialize the
/// typed Settings value.
pub fn get_settings(raw: &str) -> Result<Settings, AppError> {
    let value: serde_json::Value = serde_json::from_str(raw)
        .map_err(|e| AppError::invalid_input(&format!("could not parse settings: {}", e)))?;
    let migrated = migrate(value);
    let migrated_str = serde_json::to_string(&migrated)
        .map_err(|e| AppError::invalid_input(&format!("could not serialize settings: {}", e)))?;
    load_settings(&migrated_str)
}
