use serde::{Deserialize, Serialize};

/// A reusable query that combines free text with a set of required tags. Either
/// part may be empty: an empty `text` means "match by tags only", an empty
/// `tags` list means "match by text only". When both are present, results must
/// satisfy the text query *and* carry every listed tag.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct SearchQuery {
    #[serde(default)]
    pub text: String,
    #[serde(default)]
    pub tags: Vec<String>,
}

impl SearchQuery {
    pub fn text_only(text: &str) -> Self {
        SearchQuery {
            text: text.to_string(),
            tags: Vec::new(),
        }
    }

    pub fn tags_only(tags: &[&str]) -> Self {
        SearchQuery {
            text: String::new(),
            tags: tags.iter().map(|s| s.to_string()).collect(),
        }
    }

    pub fn new(text: &str, tags: &[&str]) -> Self {
        SearchQuery {
            text: text.to_string(),
            tags: tags.iter().map(|s| s.to_string()).collect(),
        }
    }
}
