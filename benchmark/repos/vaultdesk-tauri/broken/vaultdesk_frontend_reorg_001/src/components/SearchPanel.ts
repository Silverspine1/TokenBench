import type { SearchState } from "../state/blob.ts";

// Render the current query and its ranked results to a string.
export function renderSearchPanel(state: SearchState): string {
  const query = state.getQuery();
  const results = state.getResults();
  const header = `query: ${query}`;
  if (results.length === 0) {
    return `${header}\n(no results)`;
  }
  const lines = results.map((r) => `${r.score} ${r.id} ${r.title}`);
  return [header, ...lines].join("\n");
}
