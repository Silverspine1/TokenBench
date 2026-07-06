// Thin type surface mirroring the backend command names. In a bundled build
// these wrappers would dispatch to the native layer; here they document the
// contract and the payload shapes the UI sends.
//
// This module is also the stable barrel for the frontend integration surface:
// the UI imports the normalizers and state holders from here, so the underlying
// module layout can change without touching call sites.

export {
  normalizeFileEntry,
  normalizeError,
  type FileEntryView,
  type AppErrorView,
} from "./files.ts";
export {
  normalizeSearchResult,
  normalizeSearchResults,
  type SearchResultView,
} from "./search.ts";
export {
  normalizeSettings,
  CURRENT_SETTINGS_VERSION,
  type SettingsView,
} from "./settings.ts";
export { normalizeSaveResult, type SaveResultView } from "./notes.ts";
export { VaultState } from "../state/vaultState.ts";
export { SearchState } from "../state/searchState.ts";
export { SettingsState } from "../state/settingsState.ts";
export { NoteState } from "../state/noteState.ts";

export interface SaveNotePayload {
  path: string;
  content: string;
  expectedRevision: number;
  overwrite: boolean;
}

export const COMMAND_NAMES = [
  "open_file",
  "search",
  "get_settings",
  "save_note_with_revision",
] as const;

export type CommandName = (typeof COMMAND_NAMES)[number];

export function isCommandName(value: string): value is CommandName {
  return (COMMAND_NAMES as readonly string[]).includes(value);
}
