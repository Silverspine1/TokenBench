use vaultdesk::commands::notes::{save_note_with_revision, SaveNotePayload};
use vaultdesk::*;

fn payload(path: &str, content: &str, expected: u64, overwrite: bool) -> SaveNotePayload {
    SaveNotePayload {
        path: path.to_string(),
        content: content.to_string(),
        expected_revision: expected,
        overwrite,
    }
}

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // A save at the current revision is accepted and increments.
    {
        let mut store = NoteStore::new();
        let res = save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let ok = res.ok && !res.conflict && res.revision == 1
            && store.get("a.md").map(|n| n.content.as_str()) == Some("v1");
        r.insert(
            "current_revision_save_accepted".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // A stale save without overwrite is rejected as a conflict.
    {
        let mut store = NoteStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let res = save_note_with_revision(&mut store, payload("a.md", "stale", 0, false));
        let ok = !res.ok && res.conflict && res.current_revision == 1;
        r.insert("stale_save_rejected".into(), serde_json::Value::Bool(ok));
    }

    // A stale save with overwrite true is accepted.
    {
        let mut store = NoteStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let res = save_note_with_revision(&mut store, payload("a.md", "forced", 0, true));
        let ok = res.ok && !res.conflict && res.revision == 2
            && store.get("a.md").map(|n| n.content.as_str()) == Some("forced");
        r.insert("overwrite_allowed".into(), serde_json::Value::Bool(ok));
    }

    // A rejected stale save leaves stored content unchanged.
    {
        let mut store = NoteStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let _ = save_note_with_revision(&mut store, payload("a.md", "stale", 0, false));
        let ok = store.get("a.md").map(|n| n.content.as_str()) == Some("v1");
        r.insert(
            "content_unchanged_after_rejected".into(),
            serde_json::Value::Bool(ok),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
