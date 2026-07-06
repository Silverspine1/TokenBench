use crate::config::{load_settings, migrate};
use crate::domain::Settings;
use crate::errors::AppError;

/// Read settings for the frontend: parse the raw JSON, migrate it up to the
/// current schema version while preserving unknown fields, then materialize the
/// typed Settings value.
pub fn get_settings(raw: &str) -> Result<Settings, AppError> {
    let value: serde_json::Value = serde_json::from_str(raw)
        .map_err(|e| AppError::invalid_input(&format!("could not parse settings: {}", e)))?;
    let migrated = migrate(value);
    let migrated_str = serde_json::to_string(&migrated)
        .map_err(|e| AppError::invalid_input(&format!("could not serialize settings: {}", e)))?;
    load_settings(&migrated_str)
}
