// Thin type surface mirroring the backend command names. In a bundled build
// these wrappers would dispatch to the native layer; here they document the
// contract and the payload shapes the UI sends.
//
// This module is also the stable barrel for the frontend integration surface.
// The pieces it re-exports now live in the unsorted bin files left by the editor
// migration (./misc.ts, ../x.ts, ../y.ts, ../state/blob.ts) rather than at the
// documented api/* and state/* module paths.

export {
  normalizeFileEntry,
  normalizeError,
  normalizeSaveResult,
  type FileEntryView,
  type AppErrorView,
  type SaveResultView,
} from "./misc.ts";
export {
  normalizeSearchResult,
  normalizeSearchResults,
  type SearchResultView,
} from "../x.ts";
export {
  normalizeSettings,
  CURRENT_SETTINGS_VERSION,
  type SettingsView,
} from "../y.ts";
export { VaultState, SearchState, SettingsState } from "../state/blob.ts";
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
