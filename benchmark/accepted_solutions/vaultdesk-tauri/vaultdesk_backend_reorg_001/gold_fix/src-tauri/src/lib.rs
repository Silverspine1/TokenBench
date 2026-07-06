//! VaultDesk backend library.
//!
//! The crate models the command surface of a desktop vault application as plain
//! functions returning serde-serializable values, so every behavior is unit
//! testable offline without a window or an event loop.

pub mod commands;
pub mod config;
pub mod domain;
pub mod errors;
pub mod fs;
pub mod index;

// Key types and functions re-exported at the crate root so callers can write
// `vaultdesk::<thing>`.
pub use errors::AppError;

pub use domain::{FileEntry, Note, SearchResult, Settings, CURRENT_SETTINGS_VERSION};

pub use fs::{resolve_in_vault, scan, write_note, NoteStore};

pub use index::{tokenize, SearchIndex};

pub use config::{load_settings, migrate};

pub use commands::{
    get_settings, open_file, save_note_with_revision, search, SaveNotePayload, SaveResult,
};
