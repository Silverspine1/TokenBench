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
  const id = r.id ?? "";
  const title = r.title ?? "";
  const path = r.path ?? "";
  const snippet = r.snippet ?? "";
  const scoreRaw = r.score ?? 0;
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
