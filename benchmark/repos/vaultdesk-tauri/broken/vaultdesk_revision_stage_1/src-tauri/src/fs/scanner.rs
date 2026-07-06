use crate::domain::FileEntry;

/// Return the entries sorted deterministically by path. The input slice is left
/// untouched; a new owned vector is produced.
pub fn scan(entries: &[FileEntry]) -> Vec<FileEntry> {
    let mut out = entries.to_vec();
    out.sort_by(|a, b| a.path.cmp(&b.path));
    out
}
