// Canonical search result shape consumed by the UI.
export interface SearchResultView {
  id: string;
  title: string;
  path: string;
  snippet: string;
  score: number;
}

// Map a raw backend result into the canonical shape. Both the current backend
// shape (id, title, path, snippet, score) and an older shape (docId, name,
// location, preview, rank) are tolerated so a mixed-version response still
// normalizes cleanly.
export function normalizeSearchResult(raw: any): SearchResultView {
  const r = raw ?? {};
  const id = r.id ?? r.docId ?? "";
  const title = r.title ?? r.name ?? "";
  const path = r.path ?? r.location ?? "";
  const snippet = r.snippet ?? r.preview ?? "";
  const scoreRaw = r.score ?? r.rank ?? 0;
  const score = typeof scoreRaw === "number" ? scoreRaw : Number(scoreRaw) || 0;
  return {
    id: String(id),
    title: String(title),
    path: String(path),
    snippet: String(snippet),
    score,
  };
}

export function normalizeSearchResults(list: any[]): SearchResultView[] {
  if (!Array.isArray(list)) {
    return [];
  }
  return list.map(normalizeSearchResult);
}

// A backend invoker maps a command name and its arguments to the raw result the
// native layer would return. In a bundled build this is Tauri's `invoke`; here
// it is injected so the wrappers stay deterministic and offline-testable.
export type Invoker = (cmd: string, args: Record<string, any>) => any;

// Search notes by a single tag name. Dispatches to the `search_by_tag` backend
// command and normalizes the result list into the canonical search-result shape,
// exactly like the existing text-search path.
export function searchByTag(
  invoke: Invoker,
  tagName: string,
): SearchResultView[] {
  const raw = invoke("search_by_tag", { name: tagName });
  return normalizeSearchResults(Array.isArray(raw) ? raw : []);
}

// Plain text search wrapper, preserved unchanged: dispatches to the `search`
// backend command and normalizes its results the same way.
export function searchByText(
  invoke: Invoker,
  query: string,
): SearchResultView[] {
  const raw = invoke("search", { q: query });
  return normalizeSearchResults(Array.isArray(raw) ? raw : []);
}
