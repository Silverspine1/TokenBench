import type { SearchResultView } from "../api/search.ts";

// In-memory holder for the latest query and its results. Replacing the query
// clears prior results so a stale result set is never served after an update.
export class SearchState {
  private query = "";
  private results: SearchResultView[] = [];

  getQuery(): string {
    return this.query;
  }

  // Begin a new query. Any previously held results are dropped immediately so a
  // reader between setQuery and setResults sees an empty set, never stale data.
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
