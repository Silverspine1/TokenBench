use vaultdesk::*;

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // Canonical serialized keys on a SearchResult value.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "Title", "a.md", "needle body");
        let results = search(&idx, "needle");
        let canonical = if let Some(first) = results.first() {
            let json = serde_json::to_value(first).unwrap();
            let obj = json.as_object().cloned().unwrap_or_default();
            let keys: std::collections::BTreeSet<String> = obj.keys().cloned().collect();
            let want: std::collections::BTreeSet<String> =
                ["id", "title", "path", "snippet", "score"]
                    .iter()
                    .map(|s| s.to_string())
                    .collect();
            keys == want
        } else {
            false
        };
        r.insert(
            "rust_json_canonical_keys".into(),
            serde_json::Value::Bool(canonical),
        );
    }

    // A query that matches returns at least one result.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "Title", "a.md", "needle");
        let results = search(&idx, "needle");
        r.insert(
            "rust_query_returns_results".into(),
            serde_json::Value::Bool(!results.is_empty()),
        );
    }

    // Deterministic ordering: score desc, then id asc.
    {
        let mut idx = SearchIndex::new();
        idx.add("b", "Beta", "b.md", "alpha alpha");
        idx.add("a", "Alpha", "a.md", "alpha alpha");
        idx.add("c", "Gamma", "c.md", "alpha");
        let results = search(&idx, "alpha");
        let ids: Vec<String> = results.iter().map(|x| x.id.clone()).collect();
        r.insert(
            "sort_order_deterministic".into(),
            serde_json::Value::Bool(ids == vec!["a", "b", "c"]),
        );
    }

    // An empty corpus produces no results.
    {
        let idx = SearchIndex::new();
        let results = search(&idx, "anything");
        r.insert(
            "empty_result_empty_list".into(),
            serde_json::Value::Bool(results.is_empty()),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
