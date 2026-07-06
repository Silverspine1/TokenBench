// Thin type surface mirroring the backend command names. In a bundled build
// these wrappers would dispatch to the native layer; here they document the
// contract and the payload shapes the UI sends.

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
