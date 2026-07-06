use crate::errors::AppError;

/// Whether a path string begins with a leading separator, marking it as
/// absolute rather than vault-relative.
fn is_absolute(input: &str) -> bool {
    input.starts_with('/') || input.starts_with('\\')
}

/// Split a path on both separators and collapse `.` and `..` segments. A `..`
/// that would climb above the first segment is reported by returning an empty
/// marker through the bool flag.
fn normalize_segments(input: &str) -> Result<Vec<String>, AppError> {
    let mut out: Vec<String> = Vec::new();
    for raw in input.split(['/', '\\']) {
        match raw {
            "" | "." => continue,
            ".." => {
                if out.pop().is_none() {
                    return Err(AppError::path_escape(
                        "requested path climbs above the vault root",
                    ));
                }
            }
            other => out.push(other.to_string()),
        }
    }
    Ok(out)
}

/// Resolve a requested path against a vault root, returning a forward-slash
/// normalized canonical path guaranteed to live inside the vault.
///
/// The requested value may be absolute (sharing the vault prefix) or relative
/// to the vault root. Containment is decided segment by segment, so a sibling
/// directory whose name merely shares a string prefix with the vault — for
/// example `/vault/data-evil` against root `/vault/data` — is rejected, while a
/// genuine nested file such as `notes/sub/a.md` is accepted.
pub fn resolve_in_vault(vault_root: &str, requested: &str) -> Result<String, AppError> {
    let root_segments = normalize_segments(vault_root)?;
    let requested_segments = normalize_segments(requested)?;

    let combined: Vec<String> = if is_absolute(requested) {
        // Absolute requests are matched directly against the root segments.
        requested_segments
    } else {
        // Relative requests are appended onto the root.
        let mut c = root_segments.clone();
        c.extend(requested_segments);
        c
    };

    // Containment by segment prefix, never by raw string prefix.
    if combined.len() < root_segments.len() {
        return Err(AppError::path_escape("requested path escapes the vault"));
    }
    for (i, seg) in root_segments.iter().enumerate() {
        if &combined[i] != seg {
            return Err(AppError::path_escape("requested path escapes the vault"));
        }
    }

    Ok(combined.join("/"))
}
