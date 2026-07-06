import type { FileEntryView } from "../api/files.ts";

// In-memory holder for the current vault root and its listed entries.
export class VaultState {
  private root = "";
  private entries: FileEntryView[] = [];

  getRoot(): string {
    return this.root;
  }

  setRoot(root: string): void {
    this.root = root;
  }

  getEntries(): FileEntryView[] {
    return this.entries.slice();
  }

  setEntries(entries: FileEntryView[]): void {
    this.entries = entries.slice();
  }

  clear(): void {
    this.entries = [];
  }
}
