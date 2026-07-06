import type { NoteState } from "../state/noteState.ts";

// Render the open note's header and content to a string.
export function renderNoteEditor(state: NoteState): string {
  const path = state.getPath();
  if (path === "") {
    return "(no note open)";
  }
  return [
    `path: ${path}`,
    `revision: ${state.getRevision()}`,
    "---",
    state.getContent(),
  ].join("\n");
}
