use crate::domain::Settings;
use crate::errors::AppError;

/// Parse a raw JSON string into a Settings value. Unknown fields are preserved
/// via the flattened extra map on Settings.
pub fn load_settings(raw: &str) -> Result<Settings, AppError> {
    serde_json::from_str::<Settings>(raw)
        .map_err(|e| AppError::invalid_input(&format!("could not parse settings: {}", e)))
}
