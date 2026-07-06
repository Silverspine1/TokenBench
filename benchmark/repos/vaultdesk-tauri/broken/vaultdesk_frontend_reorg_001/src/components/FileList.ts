import type { VaultState } from "../state/blob.ts";

// Render the vault entries as plain lines. No DOM is touched; the string output
// keeps the component testable offline.
export function renderFileList(state: VaultState): string {
  const entries = state.getEntries();
  if (entries.length === 0) {
    return "(no files)";
  }
  return entries.map((e) => `${e.path} (${e.size})`).join("\n");
}
