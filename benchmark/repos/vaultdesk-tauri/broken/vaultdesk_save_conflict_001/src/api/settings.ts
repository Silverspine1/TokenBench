export const CURRENT_SETTINGS_VERSION = 2;

// Canonical settings shape consumed by the UI. Unknown keys are retained on the
// extra map so a future backend field survives a read/write round trip.
export interface SettingsView {
  version: number;
  theme: string;
  vaultRoot: string;
  extra: Record<string, unknown>;
}

const KNOWN_KEYS = new Set(["version", "theme", "vault_root", "vaultRoot"]);

// Map a raw settings object from the backend into the canonical shape.
export function normalizeSettings(raw: any): SettingsView {
  const r = raw ?? {};
  const version =
    typeof r.version === "number" ? r.version : CURRENT_SETTINGS_VERSION;
  const theme = typeof r.theme === "string" ? r.theme : "light";
  const vaultRoot =
    typeof r.vault_root === "string"
      ? r.vault_root
      : typeof r.vaultRoot === "string"
        ? r.vaultRoot
        : "";
  const extra: Record<string, unknown> = {};
  for (const key of Object.keys(r)) {
    if (!KNOWN_KEYS.has(key)) {
      extra[key] = r[key];
    }
  }
  return { version, theme, vaultRoot, extra };
}
