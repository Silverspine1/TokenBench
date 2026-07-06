import {
  normalizeSearchResults,
  type Invoker,
  type SearchResultView,
} from "./search.ts";

// A saved-search query combines free text with a set of required tags. Either
// part may be empty.
export interface SearchQuery {
  text: string;
  tags: string[];
}

// Build a normalized query value, tolerating partial inputs so callers can pass
// just text, just tags, or both.
export function makeQuery(raw: any): SearchQuery {
  const r = raw ?? {};
  const text = typeof r.text === "string" ? r.text : "";
  const tags = Array.isArray(r.tags) ? r.tags.map((t: any) => String(t)) : [];
  return { text, tags };
}

// Save a named query (text + tags). Dispatches to the `save_search` backend
// command and reports whether it was accepted.
export function saveSearch(
  invoke: Invoker,
  name: string,
  query: any,
): boolean {
  return Boolean(invoke("save_search", { name, query: makeQuery(query) }));
}

// Run a previously saved search by name. Dispatches to the `run_saved_search`
// backend command and normalizes its results into the canonical search-result
// shape, identical to text and tag searches.
export function runSavedSearch(
  invoke: Invoker,
  name: string,
): SearchResultView[] {
  const raw = invoke("run_saved_search", { name });
  return normalizeSearchResults(Array.isArray(raw) ? raw : []);
}
