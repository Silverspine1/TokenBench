use crate::domain::CURRENT_SETTINGS_VERSION;
use serde_json::{Map, Value};

/// Migrate a settings document up to the current schema version while
/// preserving every unknown field.
///
/// Version 1 used a `darkMode` boolean and lacked an explicit `theme`. The
/// migration to version 2 derives `theme` from `darkMode` when `theme` is
/// absent, removes the legacy `darkMode` key, and ensures a `vault_root` key is
/// present. A document already at the current version is returned unchanged.
pub fn migrate(value: Value) -> Value {
    let mut obj: Map<String, Value> = match value {
        Value::Object(m) => m,
        other => return other,
    };

    let version = obj
        .get("version")
        .and_then(|v| v.as_u64())
        .unwrap_or(1) as u32;

    if version >= CURRENT_SETTINGS_VERSION {
        return Value::Object(obj);
    }

    // v1 -> v2 transformations.
    if !obj.contains_key("theme") {
        let dark = obj
            .get("darkMode")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);
        let theme = if dark { "dark" } else { "light" };
        obj.insert("theme".to_string(), Value::String(theme.to_string()));
    }
    obj.remove("darkMode");

    if !obj.contains_key("vault_root") {
        obj.insert("vault_root".to_string(), Value::String(String::new()));
    }

    obj.insert(
        "version".to_string(),
        Value::from(CURRENT_SETTINGS_VERSION),
    );

    Value::Object(obj)
}
