use crate::domain::revision::Revision;
use std::collections::HashMap;

/// An in-memory history of note revisions keyed by note path. Each path owns an
/// ordered list of revisions; revision ids are assigned from a single monotonic
/// counter per path so the "current" revision is always the last one recorded
/// and every prior version stays individually addressable by its id.
///
/// This is intentionally a structured, addressable model rather than an
/// append-only opaque blob: the current revision is identifiable and any past
/// revision can be fetched by id, which is what later conflict handling relies
/// on.
#[derive(Debug, Default, Clone)]
pub struct RevisionStore {
    /// Ordered revisions per path; the last element is always the newest.
    histories: HashMap<String, Vec<Revision>>,
}

impl RevisionStore {
    pub fn new() -> Self {
        RevisionStore {
            histories: HashMap::new(),
        }
    }

    /// The revision id currently stored at a path, or 0 when the path has no
    /// recorded revisions yet.
    pub fn current_revision_id(&self, path: &str) -> u64 {
        self.histories
            .get(path)
            .and_then(|h| h.last())
            .map(|r| r.revision_id)
            .unwrap_or(0)
    }

    /// Record `content` as the next revision for `path` and return the stored
    /// revision. The new revision id is exactly one greater than the current id,
    /// keeping ids monotonic and gap-free per path.
    pub fn record(&mut self, path: &str, content: &str) -> Revision {
        let next_id = self.current_revision_id(path) + 1;
        let rev = Revision::new(next_id, content);
        self.histories
            .entry(path.to_string())
            .or_default()
            .push(rev.clone());
        rev
    }

    /// All revisions recorded for `path`, oldest first. Returns an empty slice
    /// when the path is unseen, never panicking.
    pub fn list(&self, path: &str) -> &[Revision] {
        self.histories
            .get(path)
            .map(|h| h.as_slice())
            .unwrap_or(&[])
    }

    /// The revision at `path` with the given `revision_id`, or `None` when no
    /// such revision exists.
    pub fn get(&self, path: &str, revision_id: u64) -> Option<&Revision> {
        self.histories
            .get(path)
            .and_then(|h| h.iter().find(|r| r.revision_id == revision_id))
    }

    /// The newest revision recorded for `path`, if any.
    pub fn current(&self, path: &str) -> Option<&Revision> {
        self.histories.get(path).and_then(|h| h.last())
    }
}
