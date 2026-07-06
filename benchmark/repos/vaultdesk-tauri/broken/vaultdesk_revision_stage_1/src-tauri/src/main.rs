fn main() {
    println!("VaultDesk backend v{}", env!("CARGO_PKG_VERSION"));
    println!("settings schema version: {}", vaultdesk::CURRENT_SETTINGS_VERSION);
}
