use crate::domain::SearchQuery;
use std::collections::BTreeMap;

/// An in-memory store of named, reusable queries. Names are the keys; saving the
/// same name again replaces its query. Ordering of `names()` is deterministic.
///
/// The store only persists the *query definition* (text + tags). It holds no
/// results, so a saved search always re-runs against the current index and tag
/// state — a tag removed after saving is reflected the next time it runs.
#[derive(Debug, Default, Clone)]
pub struct SavedSearchStore {
    searches: BTreeMap<String, SearchQuery>,
}

impl SavedSearchStore {
    pub fn new() -> Self {
        SavedSearchStore {
            searches: BTreeMap::new(),
        }
    }

    /// Save (or replace) a named query. An empty name is rejected.
    pub fn save(&mut self, name: &str, query: SearchQuery) -> bool {
        if name.is_empty() {
            return false;
        }
        self.searches.insert(name.to_string(), query);
        true
    }

    /// The stored query for a name, if any.
    pub fn get(&self, name: &str) -> Option<&SearchQuery> {
        self.searches.get(name)
    }

    pub fn names(&self) -> Vec<String> {
        self.searches.keys().cloned().collect()
    }
}
