use crate::domain::{SearchQuery, SearchResult};
use crate::index::{SavedSearchStore, SearchIndex, TagStore};
use std::collections::BTreeSet;

/// Save a named query combining text and tags. Replacing an existing name is
/// allowed. An empty name is rejected.
pub fn save_search(store: &mut SavedSearchStore, name: &str, query: SearchQuery) -> bool {
    store.save(name, query)
}

/// Resolve the set of note ids that carry every listed tag (AND semantics),
/// in ascending id order. An empty tag list yields `None`, meaning "no tag
/// constraint" so the text query sees the whole corpus.
fn tag_allowlist(tags: &TagStore, names: &[String]) -> Option<Vec<String>> {
    if names.is_empty() {
        return None;
    }
    let mut acc: Option<BTreeSet<String>> = None;
    for name in names {
        let ids: BTreeSet<String> = tags.notes_with_tag(name).into_iter().collect();
        acc = Some(match acc {
            None => ids,
            Some(prev) => prev.intersection(&ids).cloned().collect(),
        });
    }
    Some(acc.unwrap_or_default().into_iter().collect())
}

/// Run a saved search by name against the current index and tag state, composing
/// the text query with the tag filter through the shared search primitive.
/// Returns an empty list when the name is unknown.
pub fn run_saved_search(
    store: &SavedSearchStore,
    index: &SearchIndex,
    tags: &TagStore,
    name: &str,
) -> Vec<SearchResult> {
    let query = match store.get(name) {
        Some(q) => q.clone(),
        None => return Vec::new(),
    };
    run_query(index, tags, &query)
}

/// Execute a query value directly (text + tags) via the shared search primitive.
pub fn run_query(
    index: &SearchIndex,
    tags: &TagStore,
    query: &SearchQuery,
) -> Vec<SearchResult> {
    let allowed = tag_allowlist(tags, &query.tags);
    index.query_filtered(&query.text, allowed.as_deref())
}
