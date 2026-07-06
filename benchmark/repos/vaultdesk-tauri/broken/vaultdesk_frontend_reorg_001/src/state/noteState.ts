import { normalizeSaveResult, type SaveResultView } from "../api/misc.ts";

// In-memory holder for the open note's path, content, and known revision.
export class NoteState {
  private path = "";
  private content = "";
  private revision = 0;

  load(path: string, content: string, revision: number): void {
    this.path = path;
    this.content = content;
    this.revision = revision;
  }

  getPath(): string {
    return this.path;
  }

  getContent(): string {
    return this.content;
  }

  setContent(content: string): void {
    this.content = content;
  }

  getRevision(): number {
    return this.revision;
  }

  // Apply a save result. On a successful, non-conflicting save the local
  // revision advances to the server revision. A conflict leaves local content
  // intact and refreshes the known revision to the server's current value.
  applySaveResult(raw: any): SaveResultView {
    const result = normalizeSaveResult(raw);
    if (result.ok && !result.conflict) {
      this.revision = result.revision;
    } else if (result.conflict) {
      this.revision = result.currentRevision;
    }
    return result;
  }
}
