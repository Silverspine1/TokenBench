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
    let obj: Map<String, Value> = match value {
        Value::Object(m) => m,
        other => return other,
    };

    let theme = match obj.get("theme").and_then(|v| v.as_str()) {
        Some(t) => t.to_string(),
        None => "light".to_string(),
    };

    let vault_root = obj
        .get("vault_root")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let mut fresh: Map<String, Value> = Map::new();
    fresh.insert(
        "version".to_string(),
        Value::from(CURRENT_SETTINGS_VERSION),
    );
    fresh.insert("theme".to_string(), Value::String(theme));
    fresh.insert("vault_root".to_string(), Value::String(vault_root));

    Value::Object(fresh)
}
