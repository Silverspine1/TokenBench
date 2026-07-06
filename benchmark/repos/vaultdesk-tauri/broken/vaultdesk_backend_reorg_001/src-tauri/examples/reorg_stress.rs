//! Deterministic, offline long-output driver over the real VaultDesk backend.
//!
//! Builds a fixed corpus through the search index, runs a fixed battery of
//! queries, exercises the scanner, the revision-checked note store, and the
//! settings migration, and prints one stable line per observed result. The
//! output is a pure function of the hard-coded inputs, so it is byte-for-byte
//! reproducible and never touches the network or the clock.
//!
//! Run with `cargo run --example reorg_stress`.

use vaultdesk::{
    get_settings, open_file, save_note_with_revision, scan, search, FileEntry, NoteStore,
    SaveNotePayload, SearchIndex,
};

/// A small fixed vocabulary; queries are drawn from it deterministically.
const VOCAB: [&str; 12] = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa",
    "lambda", "mu",
];

fn doc_content(i: usize) -> String {
    // Each document mixes a deterministic subset of the vocabulary, with the
    // word at index (i % 12) repeated to create stable score spreads.
    let mut words: Vec<String> = Vec::new();
    for k in 0..6 {
        let w = VOCAB[(i + k) % VOCAB.len()];
        words.push(w.to_string());
    }
    let emphasized = VOCAB[i % VOCAB.len()];
    for _ in 0..((i % 4) + 1) {
        words.push(emphasized.to_string());
    }
    words.join(" ")
}

fn main() {
    let n_docs = 240usize;

    // Build the corpus through the real index.
    let mut idx = SearchIndex::new();
    let mut entries: Vec<FileEntry> = Vec::new();
    for i in 0..n_docs {
        let id = format!("doc-{:04}", i);
        let title = format!("Document {:04}", i);
        let path = format!("notes/{}/{}.md", i % 8, id);
        idx.add(&id, &title, &path, &doc_content(i));
        entries.push(FileEntry::new(&path, &format!("{}.md", id), (i * 7) as u64));
    }

    println!("# vaultdesk reorg stress: {} documents", n_docs);

    // Scanner: print the deterministically sorted listing.
    let sorted = scan(&entries);
    for e in &sorted {
        println!("scan\t{}\t{}\t{}", e.path, e.name, e.size);
    }

    // Search battery: run every vocabulary word as a query and print each hit.
    for q in VOCAB.iter() {
        let results = search(&idx, q);
        println!("query\t{}\t{}", q, results.len());
        for hit in &results {
            println!(
                "hit\t{}\t{}\t{}\t{:.1}\t{}",
                q, hit.id, hit.path, hit.score, hit.title
            );
        }
    }

    // Combined two-word queries for additional deterministic volume.
    for a in 0..VOCAB.len() {
        let b = (a + 3) % VOCAB.len();
        let q = format!("{} {}", VOCAB[a], VOCAB[b]);
        let results = search(&idx, &q);
        println!("query2\t{}\t{}", q, results.len());
        for hit in &results {
            println!("hit2\t{}\t{}\t{:.1}", q, hit.id, hit.score);
        }
    }

    // Note store: deterministic revision-checked saves.
    let mut store = NoteStore::new();
    for i in 0..n_docs {
        let path = format!("notes/{}/doc-{:04}.md", i % 8, i);
        let r1 = save_note_with_revision(
            &mut store,
            SaveNotePayload {
                path: path.clone(),
                content: format!("body-{}", i),
                expected_revision: 0,
                overwrite: false,
            },
        );
        // A stale save (rejected unless overwrite).
        let r2 = save_note_with_revision(
            &mut store,
            SaveNotePayload {
                path: path.clone(),
                content: format!("stale-{}", i),
                expected_revision: 0,
                overwrite: false,
            },
        );
        println!(
            "save\t{}\tok={} rev={} conflict={}",
            path, r1.ok, r1.revision, r2.conflict
        );
    }

    // Path safety + settings, printed deterministically.
    for req in [
        "notes/sub/a.md",
        "../../etc/passwd",
        "/vault/data-evil/x.md",
        "notes\\win\\b.md",
    ] {
        match open_file("/vault/data", req) {
            Ok(e) => println!("open\t{}\tOK\t{}", req, e.path),
            Err(e) => println!("open\t{}\tERR\t{}", req, e.code),
        }
    }

    for raw in [
        r#"{"version":1,"darkMode":true}"#,
        r#"{"version":1,"darkMode":false,"keep":1}"#,
        r#"{"version":2,"theme":"dark","plugin":7}"#,
    ] {
        match get_settings(raw) {
            Ok(s) => println!("settings\tv{}\ttheme={}", s.version, s.theme),
            Err(e) => println!("settings\tERR\t{}", e.code),
        }
    }

    println!("# done");
}
