use vaultdesk::*;

fn ids(results: &[SearchResult]) -> Vec<String> {
    results.iter().map(|r| r.id.clone()).collect()
}

fn fixture() -> (SearchIndex, TagStore) {
    let mut idx = SearchIndex::new();
    idx.add("n1", "One", "n1.md", "alpha alpha report");
    idx.add("n2", "Two", "n2.md", "alpha notes");
    idx.add("n3", "Three", "n3.md", "beta report");
    let mut tags = TagStore::new();
    assign_tag_to_note(&mut tags, "work", "n1");
    assign_tag_to_note(&mut tags, "work", "n3");
    assign_tag_to_note(&mut tags, "urgent", "n1");
    (idx, tags)
}

#[test]
fn run() {
    let mut r = serde_json::Map::new();
    let mut put = |k: &str, v: bool| {
        r.insert(k.to_string(), serde_json::Value::Bool(v));
    };

    // save_text_only_search: a saved text-only query runs like a plain text
    // search.
    {
        let (idx, tags) = fixture();
        let mut store = SavedSearchStore::new();
        let ok = save_search(&mut store, "by_text", SearchQuery::text_only("alpha"));
        let got = ids(&run_saved_search(&store, &idx, &tags, "by_text"));
        // n1 (alpha alpha) outscores n2 (alpha); n3 has no alpha.
        put(
            "save_text_only_search",
            ok && got == vec!["n1".to_string(), "n2".to_string()],
        );
    }

    // save_tag_only_search: a saved tag-only query returns the tagged notes.
    {
        let (idx, tags) = fixture();
        let mut store = SavedSearchStore::new();
        save_search(&mut store, "by_tag", SearchQuery::tags_only(&["work"]));
        let got = ids(&run_saved_search(&store, &idx, &tags, "by_tag"));
        put(
            "save_tag_only_search",
            got == vec!["n1".to_string(), "n3".to_string()],
        );
    }

    // save_combined_text_tag_search: text AND tags compose — only notes carrying
    // the tag and matching the text survive.
    {
        let (idx, tags) = fixture();
        let mut store = SavedSearchStore::new();
        save_search(&mut store, "combo", SearchQuery::new("report", &["work"]));
        let got = ids(&run_saved_search(&store, &idx, &tags, "combo"));
        // work => {n1, n3}; "report" matches n1 and n3 => both, n1 ties? n1 has
        // one "report", n3 has one "report" => tie, id asc.
        put(
            "save_combined_text_tag_search",
            got == vec!["n1".to_string(), "n3".to_string()],
        );
    }

    // run_saved_search_after_tag_removal: the saved query stores criteria only, so
    // removing a tag afterwards changes the result on the next run.
    {
        let (idx, mut tags) = fixture();
        let mut store = SavedSearchStore::new();
        save_search(&mut store, "by_tag", SearchQuery::tags_only(&["work"]));
        let before = ids(&run_saved_search(&store, &idx, &tags, "by_tag"));
        remove_tag_from_note(&mut tags, "work", "n1");
        let after = ids(&run_saved_search(&store, &idx, &tags, "by_tag"));
        put(
            "run_saved_search_after_tag_removal",
            before == vec!["n1".to_string(), "n3".to_string()]
                && after == vec!["n3".to_string()],
        );
    }

    // saved_search_result_shape_stable: results carry exactly the canonical keys.
    {
        let (idx, tags) = fixture();
        let mut store = SavedSearchStore::new();
        save_search(&mut store, "combo", SearchQuery::new("report", &["work"]));
        let results = run_saved_search(&store, &idx, &tags, "combo");
        let shape_ok = !results.is_empty()
            && results.iter().all(|res| {
                let json = serde_json::to_value(res).unwrap();
                let obj = json.as_object().cloned().unwrap_or_default();
                let keys: std::collections::BTreeSet<String> = obj.keys().cloned().collect();
                let want: std::collections::BTreeSet<String> =
                    ["id", "title", "path", "snippet", "score"]
                        .iter()
                        .map(|s| s.to_string())
                        .collect();
                keys == want
            });
        put("saved_search_result_shape_stable", shape_ok);
    }

    // stage1_tag_commands_unchanged: the Stage 1 tag command results are stable —
    // adding saved searches did not alter create/assign/remove/search_by_tag.
    {
        let mut idx = SearchIndex::new();
        idx.add("n1", "One", "n1.md", "alpha");
        idx.add("n2", "Two", "n2.md", "beta");
        let mut tags = TagStore::new();
        let created = create_tag(&mut tags, "work");
        let assigned = assign_tag_to_note(&mut tags, "work", "n2")
            && assign_tag_to_note(&mut tags, "work", "n1")
            && assign_tag_to_note(&mut tags, "work", "n1"); // idempotent
        let found = ids(&search_by_tag(&idx, &tags, "work"));
        let removed = remove_tag_from_note(&mut tags, "work", "n1");
        let after = ids(&search_by_tag(&idx, &tags, "work"));
        let text_ok = ids(&search(&idx, "alpha")) == vec!["n1".to_string()];
        put(
            "stage1_tag_commands_unchanged",
            created
                && assigned
                && removed
                && found == vec!["n1".to_string(), "n2".to_string()]
                && after == vec!["n2".to_string()]
                && text_ok,
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
