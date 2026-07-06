//! Hidden reorg harness for vaultdesk_backend_reorg_001.
//!
//! Each check combines a STRUCTURE gate (the relevant backend concern lives at
//! its canonical module path) with a BEHAVIOR assertion (the corresponding
//! command still works). The crate's public surface is identical in the broken
//! and gold snapshots, so behavior alone is not enough: a check passes only when
//! the behavior works AND the code lives at the canonical path. The flattened
//! broken snapshot keeps the same behavior reachable through opaque core/blob
//! piles, so its canonical paths are absent and every gated check fails.

use vaultdesk::*;

/// Path to a file relative to the crate root (the copied src-tauri).
fn canon(rel: &str) -> bool {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(rel)
        .is_file()
}

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // Canonical module paths the reorg must produce.
    let files_cmd = "src/commands/files.rs";
    let search_cmd = "src/commands/search.rs";
    let safe_path = "src/fs/safe_path.rs";
    let scanner = "src/fs/scanner.rs";
    let search_index = "src/index/search_index.rs";
    let search_result = "src/domain/search_result.rs";
    let domain_settings = "src/domain/settings.rs";

    // Opaque flattened files that must NOT remain after the reorg.
    let forbidden = ["src/core1.rs", "src/core2.rs", "src/blob.rs"];

    // --- open_file command lives under src/commands/ and resolves a vault file.
    {
        let entry = open_file("/vault/data", "notes/sub/a.md");
        let behavior = entry.as_ref().map(|e| e.path.as_str())
            == Ok("vault/data/notes/sub/a.md");
        r.insert(
            "open_file_command_at_canonical_path".into(),
            serde_json::Value::Bool(canon(files_cmd) && canon(safe_path) && behavior),
        );
    }

    // --- search command lives under src/commands/ + index under src/index/, and
    //     ranks deterministically (score desc, then id asc).
    {
        let mut idx = SearchIndex::new();
        idx.add("b", "Beta", "b.md", "alpha alpha");
        idx.add("a", "Alpha", "a.md", "alpha alpha");
        idx.add("c", "Gamma", "c.md", "alpha");
        let results = search(&idx, "alpha");
        let ids: Vec<&str> = results.iter().map(|x| x.id.as_str()).collect();
        let behavior = ids == vec!["a", "b", "c"];
        r.insert(
            "search_command_at_canonical_path".into(),
            serde_json::Value::Bool(canon(search_cmd) && canon(search_index) && behavior),
        );
    }

    // --- safe_path lives under src/fs/ and rejects traversal with the normalized
    //     error shape.
    {
        let got = open_file("/vault/data", "../../etc/passwd");
        let behavior = match got {
            Err(e) => e.code == "PATH_ESCAPE",
            Ok(_) => false,
        };
        r.insert(
            "safe_path_rejects_traversal_at_canonical_path".into(),
            serde_json::Value::Bool(canon(safe_path) && behavior),
        );
    }

    // --- scanner lives under src/fs/ and sorts entries deterministically by path.
    {
        let entries = vec![
            FileEntry::new("b.md", "b.md", 1),
            FileEntry::new("a.md", "a.md", 2),
            FileEntry::new("c/d.md", "d.md", 3),
        ];
        let sorted = scan(&entries);
        let paths: Vec<&str> = sorted.iter().map(|e| e.path.as_str()).collect();
        let behavior = paths == vec!["a.md", "b.md", "c/d.md"];
        r.insert(
            "scanner_sorts_at_canonical_path".into(),
            serde_json::Value::Bool(canon(scanner) && behavior),
        );
    }

    // --- SearchResult domain struct lives under src/domain/ and serializes the
    //     stable wire shape.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "Title", "a.md", "needle");
        let results = search(&idx, "needle");
        let behavior = match results.first() {
            Some(hit) => {
                let json = serde_json::to_value(hit).unwrap();
                ["id", "title", "path", "snippet", "score"]
                    .iter()
                    .all(|k| json.get(k).is_some())
            }
            None => false,
        };
        r.insert(
            "search_result_shape_at_canonical_path".into(),
            serde_json::Value::Bool(canon(search_result) && behavior),
        );
    }

    // --- the backend is split into the canonical module tree, not flattened into
    //     opaque catch-all piles; settings migration still works.
    {
        let all_canon = canon(files_cmd)
            && canon(search_cmd)
            && canon(safe_path)
            && canon(scanner)
            && canon(search_index)
            && canon(search_result)
            && canon(domain_settings);
        let no_forbidden = forbidden.iter().all(|f| !canon(f));
        let raw = r#"{"version":1,"darkMode":true,"customPlugin":{"keep":42}}"#;
        let behavior = match get_settings(raw) {
            Ok(s) => s.version == CURRENT_SETTINGS_VERSION && s.theme == "dark",
            Err(_) => false,
        };
        r.insert(
            "backend_modules_split_not_flattened".into(),
            serde_json::Value::Bool(all_canon && no_forbidden && behavior),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
