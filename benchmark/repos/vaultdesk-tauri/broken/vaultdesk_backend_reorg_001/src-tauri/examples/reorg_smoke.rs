//! Fast deterministic smoke check over the real VaultDesk backend command
//! surface. Prints `ok - <name>` / `not ok - <name>` for each check and exits
//! non-zero if any check fails. Offline and clock-free.
//!
//! Run with `cargo run --example reorg_smoke`.

use vaultdesk::{
    get_settings, open_file, save_note_with_revision, scan, search, FileEntry, NoteStore,
    SaveNotePayload, SearchIndex, CURRENT_SETTINGS_VERSION,
};

fn main() {
    let mut failures = 0;
    let mut check = |name: &str, cond: bool| {
        if cond {
            println!("ok - {}", name);
        } else {
            println!("not ok - {}", name);
            failures += 1;
        }
    };

    // open_file resolves a nested vault file.
    {
        let e = open_file("/vault/data", "notes/sub/a.md");
        check(
            "open_file resolves nested path",
            e.map(|x| x.path) == Ok("vault/data/notes/sub/a.md".to_string()),
        );
    }

    // open_file rejects traversal with the normalized error.
    {
        let e = open_file("/vault/data", "../../etc/passwd");
        check(
            "open_file rejects traversal",
            matches!(e, Err(ref err) if err.code == "PATH_ESCAPE"),
        );
    }

    // scanner sorts entries by path.
    {
        let sorted = scan(&[
            FileEntry::new("b.md", "b.md", 1),
            FileEntry::new("a.md", "a.md", 2),
        ]);
        let paths: Vec<&str> = sorted.iter().map(|e| e.path.as_str()).collect();
        check("scan sorts by path", paths == vec!["a.md", "b.md"]);
    }

    // search ranks by score then id.
    {
        let mut idx = SearchIndex::new();
        idx.add("b", "B", "b.md", "alpha alpha");
        idx.add("a", "A", "a.md", "alpha alpha");
        idx.add("c", "C", "c.md", "alpha");
        let ids: Vec<String> = search(&idx, "alpha").iter().map(|r| r.id.clone()).collect();
        check("search ranks by score then id", ids == vec!["a", "b", "c"]);
    }

    // search result has the stable shape.
    {
        let mut idx = SearchIndex::new();
        idx.add("a", "Title", "a.md", "needle");
        let results = search(&idx, "needle");
        let ok = results.first().map_or(false, |hit| {
            let json = serde_json::to_value(hit).unwrap();
            ["id", "title", "path", "snippet", "score"]
                .iter()
                .all(|k| json.get(k).is_some())
        });
        check("search result has stable shape", ok);
    }

    // note store enforces optimistic concurrency.
    {
        let mut store = NoteStore::new();
        let r1 = save_note_with_revision(
            &mut store,
            SaveNotePayload {
                path: "a.md".into(),
                content: "v1".into(),
                expected_revision: 0,
                overwrite: false,
            },
        );
        let r2 = save_note_with_revision(
            &mut store,
            SaveNotePayload {
                path: "a.md".into(),
                content: "stale".into(),
                expected_revision: 0,
                overwrite: false,
            },
        );
        check(
            "note save rejects stale revision",
            r1.ok && r1.revision == 1 && !r2.ok && r2.conflict,
        );
    }

    // settings migrate v1 -> current.
    {
        let s = get_settings(r#"{"version":1,"darkMode":true}"#);
        check(
            "settings migrate v1 to current",
            matches!(s, Ok(ref x) if x.version == CURRENT_SETTINGS_VERSION && x.theme == "dark"),
        );
    }

    if failures == 0 {
        println!("# all backend smoke checks passed");
    } else {
        println!("# {} backend smoke check(s) failed", failures);
        std::process::exit(1);
    }
}
