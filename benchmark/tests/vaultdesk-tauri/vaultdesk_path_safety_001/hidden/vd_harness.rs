use vaultdesk::*;

#[test]
fn run() {
    let mut r = serde_json::Map::new();

    // A genuine nested file inside the vault resolves.
    {
        let got = resolve_in_vault("/vault/data", "notes/sub/a.md");
        r.insert(
            "nested_valid_accepted".into(),
            serde_json::Value::Bool(got.as_deref() == Ok("vault/data/notes/sub/a.md")),
        );
    }

    // A traversal that climbs above the root is rejected.
    {
        let got = resolve_in_vault("/vault/data", "../../etc/passwd");
        r.insert(
            "traversal_rejected".into(),
            serde_json::Value::Bool(got.is_err()),
        );
    }

    // A sibling sharing a string prefix is rejected.
    {
        let got = resolve_in_vault("/vault/data", "/vault/data-evil/x.md");
        r.insert(
            "sibling_prefix_rejected".into(),
            serde_json::Value::Bool(got.is_err()),
        );
    }

    // Windows-style separators normalize to forward slashes and resolve to the
    // same path as the POSIX-separator equivalent request.
    {
        let win = resolve_in_vault("C:\\vault", "notes\\a.md");
        let posix = resolve_in_vault("C:/vault", "notes/a.md");
        let ok = win.as_deref() == Ok("C:/vault/notes/a.md")
            && win == posix;
        r.insert(
            "windows_separator".into(),
            serde_json::Value::Bool(ok),
        );
    }

    // POSIX-style separators resolve the same way.
    {
        let got = resolve_in_vault("/vault/data", "/vault/data/notes/x.md");
        r.insert(
            "posix_separator".into(),
            serde_json::Value::Bool(got.as_deref() == Ok("vault/data/notes/x.md")),
        );
    }

    // A clearly-outside absolute path returns a normalized error with code + message.
    {
        let got = resolve_in_vault("/vault/data", "/etc/passwd");
        let ok = match got {
            Err(e) => !e.code.is_empty() && !e.message.is_empty(),
            Ok(_) => false,
        };
        r.insert(
            "error_shape_normalized".into(),
            serde_json::Value::Bool(ok),
        );
    }

    let out = std::env::var("VD_OUT").expect("VD_OUT");
    std::fs::write(out, serde_json::to_string(&r).unwrap()).unwrap();
}
