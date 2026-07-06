use vaultdesk::commands::notes::{save_note_with_revision, SaveNotePayload};
use vaultdesk::{
    get_settings, open_file, resolve_in_vault, scan, search, tokenize, AppError, FileEntry,
    NoteStore, SearchIndex, CURRENT_SETTINGS_VERSION,
};

#[test]
fn resolve_accepts_nested_file() {
    let got = resolve_in_vault("/vault/data", "notes/sub/a.md").unwrap();
    assert_eq!(got, "vault/data/notes/sub/a.md");
}

#[test]
fn resolve_rejects_sibling_prefix() {
    let err = resolve_in_vault("/vault/data", "/vault/data-evil").unwrap_err();
    assert_eq!(err.code, "PATH_ESCAPE");
}

#[test]
fn resolve_rejects_traversal() {
    let err = resolve_in_vault("/vault/data", "..\\secret.txt").unwrap_err();
    assert_eq!(err.code, "PATH_ESCAPE");
}

#[test]
fn resolve_accepts_absolute_inside_vault() {
    let got = resolve_in_vault("/vault/data", "/vault/data/notes/x.md").unwrap();
    assert_eq!(got, "vault/data/notes/x.md");
}

#[test]
fn resolve_normalizes_backslashes() {
    let got = resolve_in_vault("C:\\vault", "notes\\a.md").unwrap();
    assert_eq!(got, "C:/vault/notes/a.md");
}

#[test]
fn open_file_reports_path_escape() {
    let err: AppError = open_file("/vault/data", "../../etc/passwd").unwrap_err();
    assert_eq!(err.code, "PATH_ESCAPE");
}

#[test]
fn scan_sorts_by_path() {
    let entries = vec![
        FileEntry::new("b.md", "b.md", 1),
        FileEntry::new("a.md", "a.md", 2),
        FileEntry::new("c/d.md", "d.md", 3),
    ];
    let sorted = scan(&entries);
    let paths: Vec<&str> = sorted.iter().map(|e| e.path.as_str()).collect();
    assert_eq!(paths, vec!["a.md", "b.md", "c/d.md"]);
}

#[test]
fn tokenize_lowercases_and_splits() {
    assert_eq!(tokenize("Hello, World-42!"), vec!["hello", "world", "42"]);
    assert!(tokenize("   ").is_empty());
}

#[test]
fn query_orders_by_score_then_id() {
    let mut idx = SearchIndex::new();
    idx.add("b", "Beta", "b.md", "alpha alpha");
    idx.add("a", "Alpha", "a.md", "alpha alpha");
    idx.add("c", "Gamma", "c.md", "alpha");
    let results = search(&idx, "alpha");
    let ids: Vec<&str> = results.iter().map(|r| r.id.as_str()).collect();
    // b and a tie on score (2.0); a sorts before b. c has score 1.0.
    assert_eq!(ids, vec!["a", "b", "c"]);
}

#[test]
fn query_excludes_removed_and_reflects_updates() {
    let mut idx = SearchIndex::new();
    idx.add("a", "A", "a.md", "needle");
    idx.add("b", "B", "b.md", "needle");
    idx.remove("a");
    idx.update("b", "haystack");
    idx.rename("b", "moved/b.md");
    let by_needle = search(&idx, "needle");
    assert!(by_needle.is_empty());
    let by_hay = search(&idx, "haystack");
    assert_eq!(by_hay.len(), 1);
    assert_eq!(by_hay[0].path, "moved/b.md");
}

#[test]
fn rescan_rebuilds_corpus() {
    let mut idx = SearchIndex::new();
    idx.add("old", "Old", "old.md", "stale");
    idx.rescan(&[(
        "new".to_string(),
        "New".to_string(),
        "new.md".to_string(),
        "fresh".to_string(),
    )]);
    assert!(search(&idx, "stale").is_empty());
    assert_eq!(search(&idx, "fresh").len(), 1);
}

#[test]
fn migrate_v1_preserves_unknown_fields() {
    let raw = r#"{"version":1,"darkMode":true,"customPlugin":{"keep":42}}"#;
    let settings = get_settings(raw).unwrap();
    assert_eq!(settings.version, CURRENT_SETTINGS_VERSION);
    assert_eq!(settings.theme, "dark");
    assert_eq!(
        settings.extra.get("customPlugin").and_then(|v| v.get("keep")),
        Some(&serde_json::json!(42))
    );
    assert!(settings.extra.get("darkMode").is_none());
}

#[test]
fn migrate_current_version_unchanged() {
    let raw = r#"{"version":2,"theme":"dark","vault_root":"/v","plugin":1}"#;
    let settings = get_settings(raw).unwrap();
    assert_eq!(settings.version, 2);
    assert_eq!(settings.theme, "dark");
    assert_eq!(settings.extra.get("plugin"), Some(&serde_json::json!(1)));
}

#[test]
fn save_note_accepts_matching_revision() {
    let mut store = NoteStore::new();
    let r = save_note_with_revision(
        &mut store,
        SaveNotePayload {
            path: "a.md".to_string(),
            content: "v1".to_string(),
            expected_revision: 0,
            overwrite: false,
        },
    );
    assert!(r.ok);
    assert!(!r.conflict);
    assert_eq!(r.revision, 1);
    assert_eq!(store.get("a.md").unwrap().content, "v1");
}

#[test]
fn save_note_rejects_stale_without_overwrite() {
    let mut store = NoteStore::new();
    save_note_with_revision(
        &mut store,
        SaveNotePayload {
            path: "a.md".to_string(),
            content: "v1".to_string(),
            expected_revision: 0,
            overwrite: false,
        },
    );
    let r = save_note_with_revision(
        &mut store,
        SaveNotePayload {
            path: "a.md".to_string(),
            content: "stale".to_string(),
            expected_revision: 0,
            overwrite: false,
        },
    );
    assert!(!r.ok);
    assert!(r.conflict);
    assert_eq!(r.current_revision, 1);
    assert_eq!(store.get("a.md").unwrap().content, "v1");
}

#[test]
fn save_note_overwrite_forces_stale_save() {
    let mut store = NoteStore::new();
    save_note_with_revision(
        &mut store,
        SaveNotePayload {
            path: "a.md".to_string(),
            content: "v1".to_string(),
            expected_revision: 0,
            overwrite: false,
        },
    );
    let r = save_note_with_revision(
        &mut store,
        SaveNotePayload {
            path: "a.md".to_string(),
            content: "forced".to_string(),
            expected_revision: 0,
            overwrite: true,
        },
    );
    assert!(r.ok);
    assert!(!r.conflict);
    assert_eq!(r.revision, 2);
    assert_eq!(store.get("a.md").unwrap().content, "forced");
}

#[test]
fn search_result_serializes_expected_fields() {
    let mut idx = SearchIndex::new();
    idx.add("a", "Title", "a.md", "needle");
    let results = search(&idx, "needle");
    let json = serde_json::to_value(&results[0]).unwrap();
    for key in ["id", "title", "path", "snippet", "score"] {
        assert!(json.get(key).is_some(), "missing field {}", key);
    }
}
