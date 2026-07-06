use vaultdesk::*;

fn ids(results: &[SearchResult]) -> Vec<String> {
    results.iter().map(|r| r.id.clone()).collect()
}

#[test]
fn run() {
    let mut r = serde_json::Map::new();
    let mut put = |k: &str, v: bool| {
        r.insert(k.to_string(), serde_json::Value::Bool(v));
    };

    // create_tag: a freshly created tag exists.
    {
        let mut tags = TagStore::new();
        let ok = create_tag(&mut tags, "work");
        put("create_tag", ok && tags.has_tag("work"));
    }

    // assign_tag: after assigning, search_by_tag returns the note.
    {
        let mut idx = SearchIndex::new();
        idx.add("n1", "Note One", "n1.md", "alpha body");
        idx.add("n2", "Note Two", "n2.md", "beta body");
        let mut tags = TagStore::new();
        create_tag(&mut tags, "work");
        let ok = assign_tag_to_note(&mut tags, "work", "n1");
        let found = ids(&search_by_tag(&idx, &tags, "work"));
        put("assign_tag", ok && found == vec!["n1".to_string()]);
    }

    // remove_tag: after removing, the note no longer appears under the tag.
    {
        let mut idx = SearchIndex::new();
        idx.add("n1", "Note One", "n1.md", "alpha body");
        let mut tags = TagStore::new();
        assign_tag_to_note(&mut tags, "work", "n1");
        let ok = remove_tag_from_note(&mut tags, "work", "n1");
        let found = ids(&search_by_tag(&idx, &tags, "work"));
        put("remove_tag", ok && found.is_empty());
    }

    // search_by_tag: returns exactly the tagged notes, in deterministic id order,
    // with the canonical search-result shape.
    {
        let mut idx = SearchIndex::new();
        idx.add("n1", "One", "n1.md", "alpha");
        idx.add("n2", "Two", "n2.md", "beta");
        idx.add("n3", "Three", "n3.md", "gamma");
        let mut tags = TagStore::new();
        assign_tag_to_note(&mut tags, "work", "n3");
        assign_tag_to_note(&mut tags, "work", "n1");
        let results = search_by_tag(&idx, &tags, "work");
        let order_ok = ids(&results) == vec!["n1".to_string(), "n3".to_string()];
        let shape_ok = results.iter().all(|res| {
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
        put("search_by_tag", order_ok && shape_ok);
    }

    // duplicate_tag_assignment_idempotent: assigning the same pair twice leaves a
    // single membership.
    {
        let mut idx = SearchIndex::new();
        idx.add("n1", "One", "n1.md", "alpha");
        let mut tags = TagStore::new();
        assign_tag_to_note(&mut tags, "work", "n1");
        assign_tag_to_note(&mut tags, "work", "n1");
        let found = ids(&search_by_tag(&idx, &tags, "work"));
        put(
            "duplicate_tag_assignment_idempotent",
            found == vec!["n1".to_string()],
        );
    }

    // text_search_still_works: the existing text path is unchanged and composes
    // independently of tags.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "Alpha", "a.md", "needle needle");
        idx.add("b", "Beta", "b.md", "needle");
        idx.add("c", "Gamma", "c.md", "haystack");
        let results = search(&idx, "needle");
        let order_ok = ids(&results) == vec!["a".to_string(), "b".to_string()];
        put("text_search_still_works", order_ok);
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
