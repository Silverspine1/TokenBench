use crate::domain::FileEntry;
use crate::errors::AppError;
use crate::fs::resolve_in_vault;

/// Resolve and describe a file inside the vault. The path is validated against
/// the vault boundary before any entry is produced; on rejection the normalized
/// error shape is returned for the frontend.
pub fn open_file(vault_root: &str, requested: &str) -> Result<FileEntry, AppError> {
    let resolved = resolve_in_vault(vault_root, requested)?;
    let name = resolved
        .rsplit('/')
        .next()
        .unwrap_or(&resolved)
        .to_string();
    Ok(FileEntry::new(&resolved, &name, 0))
}
