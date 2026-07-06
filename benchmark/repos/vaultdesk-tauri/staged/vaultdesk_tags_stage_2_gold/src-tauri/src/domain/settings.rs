use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

/// The settings schema version this build reads and writes.
pub const CURRENT_SETTINGS_VERSION: u32 = 2;

/// User settings. Unknown fields are preserved verbatim through load and
/// migration so that newer keys written by a future build are not discarded.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Settings {
    pub version: u32,
    #[serde(default)]
    pub theme: String,
    #[serde(default)]
    pub vault_root: String,
    #[serde(flatten)]
    pub extra: Map<String, Value>,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            version: CURRENT_SETTINGS_VERSION,
            theme: "light".to_string(),
            vault_root: String::new(),
            extra: Map::new(),
        }
    }
}
