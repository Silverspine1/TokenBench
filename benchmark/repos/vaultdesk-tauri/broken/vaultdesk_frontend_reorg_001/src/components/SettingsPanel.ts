import type { SettingsState } from "../state/blob.ts";

// Render the active settings to a string.
export function renderSettingsPanel(state: SettingsState): string {
  const s = state.get();
  const extraKeys = Object.keys(s.extra).sort();
  const extra = extraKeys.length > 0 ? extraKeys.join(",") : "(none)";
  return [
    `version: ${s.version}`,
    `theme: ${s.theme}`,
    `vaultRoot: ${s.vaultRoot}`,
    `extra: ${extra}`,
  ].join("\n");
}
