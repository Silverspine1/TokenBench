// Catch-all state file. Three independent in-memory holders were flattened into
// this single blob during the migration: the vault listing, the search query and
// its results, and the active settings. Their imports were rewired to the
// unsorted bin modules (../x.ts, ../y.ts) since the documented api/* modules were
// emptied out.

import type { FileEntryView } from "../api/misc.ts";
import type { SearchResultView } from "../x.ts";
import {
  normalizeSettings,
  CURRENT_SETTINGS_VERSION,
  type SettingsView,
} from "../y.ts";

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

// In-memory holder for the latest query and its results. Replacing the query
// clears prior results so a stale result set is never served after an update.
export class SearchState {
  private query = "";
  private results: SearchResultView[] = [];

  getQuery(): string {
    return this.query;
  }

  setQuery(query: string): void {
    this.query = query;
    this.results = [];
  }

  getResults(): SearchResultView[] {
    return this.results.slice();
  }

  setResults(results: SearchResultView[]): void {
    this.results = results.slice();
  }

  clear(): void {
    this.query = "";
    this.results = [];
  }
}

// In-memory holder for the active settings.
export class SettingsState {
  private settings: SettingsView = {
    version: CURRENT_SETTINGS_VERSION,
    theme: "light",
    vaultRoot: "",
    extra: {},
  };

  get(): SettingsView {
    return { ...this.settings, extra: { ...this.settings.extra } };
  }

  set(raw: any): void {
    this.settings = normalizeSettings(raw);
  }

  getTheme(): string {
    return this.settings.theme;
  }
}
