use vaultdesk::*;

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // A created note is indexed and findable.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "A", "a.md", "needle");
        r.insert(
            "create_indexed".into(),
            serde_json::Value::Bool(search(&idx, "needle").len() == 1),
        );
    }

    // After update, a word from the new content is found and an old-only word is not.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "A", "a.md", "needle");
        idx.update("a", "haystack");
        let new_found = search(&idx, "haystack").len() == 1;
        let old_gone = search(&idx, "needle").is_empty();
        r.insert(
            "update_reflected".into(),
            serde_json::Value::Bool(new_found && old_gone),
        );
    }

    // After remove, the document no longer appears.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "A", "a.md", "needle");
        idx.add("b", "B", "b.md", "needle");
        idx.remove("a");
        let results = search(&idx, "needle");
        let gone = results.iter().all(|x| x.id != "a");
        r.insert("delete_disappears".into(), serde_json::Value::Bool(gone));
    }

    // A renamed document reports its new path.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "A", "a.md", "needle");
        idx.rename("a", "moved/a.md");
        let results = search(&idx, "needle");
        let ok = results.first().map(|x| x.path.as_str()) == Some("moved/a.md");
        r.insert("rename_path_updated".into(), serde_json::Value::Bool(ok));
    }

    // A full rescan rebuilds the corpus from scratch.
    {
        let mut idx = SearchIndex::new();
        idx.add("old", "Old", "old.md", "stale");
        idx.rescan(&[(
            "new".to_string(),
            "New".to_string(),
            "new.md".to_string(),
            "fresh".to_string(),
        )]);
        let ok = search(&idx, "stale").is_empty() && search(&idx, "fresh").len() == 1;
        r.insert("rescan_rebuilds".into(), serde_json::Value::Bool(ok));
    }

    // The tokenizer lowercases input.
    {
        let toks = tokenize("Hello WORLD");
        r.insert(
            "tokenizer_lowercases".into(),
            serde_json::Value::Bool(toks == vec!["hello", "world"]),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
