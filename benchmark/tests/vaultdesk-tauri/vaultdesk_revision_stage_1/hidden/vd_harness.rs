// Hidden harness for vaultdesk_revision_stage_1. Exercises the new note
// revision-history surface and confirms ordinary note save/load is unaffected.
// Emits a JSON map of check-name -> bool to $VD_OUT for per-check partial credit.

use vaultdesk::commands::revisions::{
    get_note_revision, list_note_revisions, save_note_revision,
};
use vaultdesk::fs::revision_store::RevisionStore;
use vaultdesk::{write_note, NoteStore};

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // first_revision: the first recorded revision of a fresh path gets id 1 and
    // stores the exact content.
    {
        let mut store = RevisionStore::new();
        let rev = save_note_revision(&mut store, "a.md", "hello");
        let ok = rev.revision_id == 1
            && rev.content == "hello"
            && store.current_revision_id("a.md") == 1;
        r.insert("first_revision".into(), serde_json::Value::Bool(ok));
    }

    // multiple_revisions: successive saves of the same path get strictly
    // increasing, gap-free ids and the history retains every version's content.
    {
        let mut store = RevisionStore::new();
        save_note_revision(&mut store, "a.md", "v1");
        save_note_revision(&mut store, "a.md", "v2");
        let third = save_note_revision(&mut store, "a.md", "v3");
        let hist = list_note_revisions(&store, "a.md");
        let ok = third.revision_id == 3
            && hist.len() == 3
            && hist[0].content == "v1"
            && hist[1].content == "v2"
            && hist[2].content == "v3"
            && store.current_revision_id("a.md") == 3;
        r.insert("multiple_revisions".into(), serde_json::Value::Bool(ok));
    }

    // list_order_deterministic: revisions are returned oldest-first, strictly
    // ascending by revision id, and the ordering is independent of how paths are
    // interleaved.
    {
        let mut store = RevisionStore::new();
        save_note_revision(&mut store, "a.md", "a1");
        save_note_revision(&mut store, "b.md", "b1");
        save_note_revision(&mut store, "a.md", "a2");
        save_note_revision(&mut store, "a.md", "a3");
        let hist = list_note_revisions(&store, "a.md");
        let ids: Vec<u64> = hist.iter().map(|x| x.revision_id).collect();
        let contents: Vec<&str> = hist.iter().map(|x| x.content.as_str()).collect();
        let ascending = ids.windows(2).all(|w| w[0] < w[1]);
        let ok = ids == vec![1, 2, 3]
            && ascending
            && contents == vec!["a1", "a2", "a3"];
        r.insert(
            "list_order_deterministic".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // get_specific_revision: any past revision is addressable by id, and an
    // unknown id returns None.
    {
        let mut store = RevisionStore::new();
        save_note_revision(&mut store, "a.md", "first");
        save_note_revision(&mut store, "a.md", "second");
        save_note_revision(&mut store, "a.md", "third");
        let got1 = get_note_revision(&store, "a.md", 1);
        let got2 = get_note_revision(&store, "a.md", 2);
        let missing = get_note_revision(&store, "a.md", 99);
        let ok = got1.as_ref().map(|x| x.content.as_str()) == Some("first")
            && got2.as_ref().map(|x| x.content.as_str()) == Some("second")
            && missing.is_none();
        r.insert("get_specific_revision".into(), serde_json::Value::Bool(ok));
    }

    // normal_save_load_still_works: the ordinary note store (used by normal
    // save/load) keeps behaving as before, independent of the revision history.
    {
        let mut notes = NoteStore::new();
        write_note(&mut notes, "n.md", "body", 1);
        let loaded = notes.get("n.md").map(|n| n.content.as_str());
        let rev = notes.current_revision("n.md");
        let ok = loaded == Some("body") && rev == 1;
        r.insert(
            "normal_save_load_still_works".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // metadata_preserved: each revision carries content-derived metadata that is
    // retained in history (not recomputed lossily on read).
    {
        let mut store = RevisionStore::new();
        save_note_revision(&mut store, "a.md", "one\ntwo\nthree");
        save_note_revision(&mut store, "a.md", "");
        let hist = list_note_revisions(&store, "a.md");
        let ok = hist.len() == 2
            && hist[0].meta.byte_len == 13
            && hist[0].meta.line_count == 3
            && hist[1].meta.byte_len == 0
            && hist[1].meta.line_count == 0;
        r.insert("metadata_preserved".into(), serde_json::Value::Bool(ok));
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
