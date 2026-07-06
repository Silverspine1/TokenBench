//! VaultDesk backend library.
//!
//! The crate models the command surface of a desktop vault application as plain
//! functions returning serde-serializable values, so every behavior is unit
//! testable offline without a window or an event loop.
//!
//! The backend implementation currently lives in a few consolidated piles
//! (`blob`, `core1`, `core2`) left over from an import; the crate root re-exports
//! the public surface from them.

mod blob;
mod core1;
mod core2;
pub mod errors;

// Key types and functions re-exported at the crate root so callers can write
// `vaultdesk::<thing>`.
pub use errors::AppError;

pub use blob::{FileEntry, Note, SearchResult, Settings, CURRENT_SETTINGS_VERSION};

pub use core1::{
    open_file, resolve_in_vault, save_note_with_revision, scan, write_note, NoteStore,
    SaveNotePayload, SaveResult,
};

pub use core2::{get_settings, load_settings, migrate, search, tokenize, SearchIndex};
