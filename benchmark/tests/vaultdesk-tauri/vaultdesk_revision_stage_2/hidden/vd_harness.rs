// Hidden harness for vaultdesk_revision_stage_2. Exercises revision-checked
// conflict detection layered on the Stage 1 revision history, and confirms the
// Stage 1 history surface still behaves. Emits a JSON map of check-name -> bool
// to $VD_OUT for per-check partial credit.

use vaultdesk::commands::notes::{save_note_with_revision, SaveNotePayload};
use vaultdesk::commands::revisions::{
    get_note_revision, list_note_revisions, save_note_revision,
};
use vaultdesk::fs::revision_store::RevisionStore;

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

    // same_revision_save: a save whose expectedRevision matches the current
    // revision id is accepted and advances the revision.
    {
        let mut store = RevisionStore::new();
        let res = save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let ok = res.ok
            && !res.conflict
            && res.revision == 1
            && store.current_revision_id("a.md") == 1
            && store.current("a.md").map(|x| x.content.as_str()) == Some("v1");
        r.insert("same_revision_save".into(), serde_json::Value::Bool(ok));
    }

    // stale_save_rejected: a save with a stale expectedRevision and overwrite
    // false is rejected as a conflict and is NOT recorded.
    {
        let mut store = RevisionStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let res = save_note_with_revision(&mut store, payload("a.md", "stale", 0, false));
        let ok = !res.ok
            && res.conflict
            && store.current_revision_id("a.md") == 1
            && list_note_revisions(&store, "a.md").len() == 1;
        r.insert("stale_save_rejected".into(), serde_json::Value::Bool(ok));
    }

    // explicit_overwrite_allowed: a stale save with overwrite true is accepted
    // and recorded as a new revision.
    {
        let mut store = RevisionStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        let res = save_note_with_revision(&mut store, payload("a.md", "forced", 0, true));
        let ok = res.ok
            && !res.conflict
            && res.revision == 2
            && store.current("a.md").map(|x| x.content.as_str()) == Some("forced");
        r.insert("explicit_overwrite_allowed".into(), serde_json::Value::Bool(ok));
    }

    // conflict_returns_current_revision: a rejected stale save reports the actual
    // current revision id so the client can re-sync.
    {
        let mut store = RevisionStore::new();
        save_note_with_revision(&mut store, payload("a.md", "v1", 0, false));
        save_note_with_revision(&mut store, payload("a.md", "v2", 1, false));
        let res = save_note_with_revision(&mut store, payload("a.md", "stale", 1, false));
        let ok = !res.ok && res.conflict && res.current_revision == 2;
        r.insert(
            "conflict_returns_current_revision".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // content_unchanged_after_rejected_save: the stored current content is left
    // untouched after a rejected stale save.
    {
        let mut store = RevisionStore::new();
        save_note_with_revision(&mut store, payload("a.md", "keep", 0, false));
        let _ = save_note_with_revision(&mut store, payload("a.md", "clobber", 0, false));
        let ok = store.current("a.md").map(|x| x.content.as_str()) == Some("keep");
        r.insert(
            "content_unchanged_after_rejected_save".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // stage1_revision_apis_unchanged: the Stage 1 history surface still records,
    // lists, and fetches revisions exactly as before.
    {
        let mut store = RevisionStore::new();
        save_note_revision(&mut store, "h.md", "one");
        save_note_revision(&mut store, "h.md", "two");
        let hist = list_note_revisions(&store, "h.md");
        let got = get_note_revision(&store, "h.md", 1);
        let ok = hist.len() == 2
            && hist[0].revision_id == 1
            && hist[1].revision_id == 2
            && got.as_ref().map(|x| x.content.as_str()) == Some("one");
        r.insert(
            "stage1_revision_apis_unchanged".into(),
            serde_json::Value::Bool(ok),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
