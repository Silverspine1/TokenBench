// Second unsorted bin file. Holds the settings surface that the UI consumes,
// landed here during the same migration that produced src/x.ts.

export const CURRENT_SETTINGS_VERSION = 2;

export interface SettingsView {
  version: number;
  theme: string;
  vaultRoot: string;
  extra: Record<string, unknown>;
}

const KNOWN_KEYS = new Set(["version", "theme", "vault_root", "vaultRoot"]);

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
