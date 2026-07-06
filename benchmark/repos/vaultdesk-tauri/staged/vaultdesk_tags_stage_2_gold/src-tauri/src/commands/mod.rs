pub mod files;
pub mod notes;
pub mod saved_search;
pub mod search;
pub mod settings;
pub mod tags;

pub use files::open_file;
pub use notes::{save_note_with_revision, SaveNotePayload, SaveResult};
pub use saved_search::{run_query, run_saved_search, save_search};
pub use search::search;
pub use settings::get_settings;
pub use tags::{assign_tag_to_note, create_tag, remove_tag_from_note, search_by_tag};
