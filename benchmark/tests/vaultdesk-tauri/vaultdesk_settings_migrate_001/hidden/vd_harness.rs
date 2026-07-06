use vaultdesk::*;

#[test]
fn run() {
    use serde_json::json;
    let mut r = serde_json::Map::new();

    // A v1 document migrates to the current version.
    {
        let migrated = migrate(json!({"version": 1, "darkMode": true}));
        let ok = migrated.get("version").and_then(|v| v.as_u64())
            == Some(CURRENT_SETTINGS_VERSION as u64)
            && migrated.get("theme").and_then(|v| v.as_str()) == Some("dark");
        r.insert("v1_migrates_to_current".into(), serde_json::Value::Bool(ok));
    }

    // A partially-populated v2 document keeps its current version and theme.
    {
        let migrated = migrate(json!({"version": 2, "theme": "dark"}));
        let ok = migrated.get("version").and_then(|v| v.as_u64())
            == Some(CURRENT_SETTINGS_VERSION as u64)
            && migrated.get("theme").and_then(|v| v.as_str()) == Some("dark");
        r.insert("partial_v2_config".into(), serde_json::Value::Bool(ok));
    }

    // A field unknown to the migration survives a v1 -> v2 migration.
    {
        let migrated = migrate(json!({"version": 1, "darkMode": false, "customField": 42}));
        let ok = migrated.get("customField").and_then(|v| v.as_u64()) == Some(42);
        r.insert("unknown_field_preserved".into(), serde_json::Value::Bool(ok));
    }

    // A document already at the current version is left byte-equal.
    {
        let original = json!({"version": 2, "theme": "dark", "vault_root": "/v", "plugin": 1});
        let migrated = migrate(original.clone());
        let ok = migrated == original;
        r.insert("already_current_unchanged".into(), serde_json::Value::Bool(ok));
    }

    // The frontend can read a migrated document and find vault_root.
    {
        let migrated = migrate(json!({"version": 1, "darkMode": true}));
        let text = serde_json::to_string(&migrated).unwrap();
        let reparsed: serde_json::Value = serde_json::from_str(&text).unwrap();
        let ok = reparsed.get("vault_root").is_some();
        r.insert("frontend_reads_migrated".into(), serde_json::Value::Bool(ok));
    }

    // An absent optional field receives its default on migration.
    {
        let migrated = migrate(json!({"version": 1, "darkMode": false}));
        let ok = migrated.get("vault_root").and_then(|v| v.as_str()) == Some("");
        r.insert("missing_optional_default".into(), serde_json::Value::Bool(ok));
    }

    // A v1 document whose darkMode is true derives a dark theme.
    {
        let migrated = migrate(json!({"version": 1, "darkMode": true}));
        let ok = migrated.get("theme").and_then(|v| v.as_str()) == Some("dark");
        r.insert("darkmode_true_maps_dark".into(), serde_json::Value::Bool(ok));
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
