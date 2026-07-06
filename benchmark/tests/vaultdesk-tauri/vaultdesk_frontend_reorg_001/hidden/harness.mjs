// Hidden harness for the VaultDesk frontend reorg. Each behavioural check is
// gated on the relevant module existing at its CANONICAL path (src/api/* and
// src/state/*). The flattened "broken" layout keeps the same behaviour reachable
// through unsorted bin files, so behaviour alone is not enough: a check passes
// only when the behaviour works AND the code lives at the canonical module path.
// Each check imports independently inside try/catch so a missing canonical module
// fails only its own checks (graceful partial credit).

import { pathToFileURL } from "node:url";
import path from "node:path";

const ws = process.env.TOKENBENCH_WORKSPACE;
if (!ws) {
  console.error("TOKENBENCH_WORKSPACE not set");
  process.exit(2);
}

function canonUrl(...parts) {
  return pathToFileURL(path.join(ws, ...parts)).href;
}

const r = {};

// --- src/api/files.ts exists as a real module and normalizes a file entry ---
try {
  const m = await import(canonUrl("src", "api", "files.ts"));
  const fe = m.normalizeFileEntry({ path: "a.md", name: "a", size: "12" });
  r.files_module_canonical =
    fe.path === "a.md" && fe.name === "a" && fe.size === 12;
} catch {
  r.files_module_canonical = false;
}

// --- src/api/search.ts exists and normalizes both backend shapes ---
try {
  const m = await import(canonUrl("src", "api", "search.ts"));
  const a = m.normalizeSearchResult({
    id: "a",
    title: "Alpha",
    path: "a.md",
    snippet: "hello",
    score: 2,
  });
  const b = m.normalizeSearchResult({
    docId: "b",
    name: "Beta",
    location: "b.md",
    preview: "world",
    rank: 3,
  });
  const empty = m.normalizeSearchResults("nope");
  r.search_module_canonical =
    a.id === "a" &&
    a.snippet === "hello" &&
    a.score === 2 &&
    b.id === "b" &&
    b.title === "Beta" &&
    b.snippet === "world" &&
    b.score === 3 &&
    Array.isArray(empty) &&
    empty.length === 0;
} catch {
  r.search_module_canonical = false;
}

// --- src/api/settings.ts exists and normalizes settings, keeping unknown keys ---
try {
  const m = await import(canonUrl("src", "api", "settings.ts"));
  const s = m.normalizeSettings({
    version: 2,
    theme: "dark",
    vault_root: "/v",
    plugin: { keep: 42 },
  });
  r.settings_module_canonical =
    m.CURRENT_SETTINGS_VERSION === 2 &&
    s.version === 2 &&
    s.theme === "dark" &&
    s.vaultRoot === "/v" &&
    s.extra.plugin !== undefined;
} catch {
  r.settings_module_canonical = false;
}

// --- src/api/notes.ts exists and normalizes a save result ---
try {
  const m = await import(canonUrl("src", "api", "notes.ts"));
  const sr = m.normalizeSaveResult({
    ok: false,
    revision: 1,
    conflict: true,
    current_revision: 7,
  });
  r.notes_module_canonical =
    sr.ok === false &&
    sr.conflict === true &&
    sr.revision === 1 &&
    sr.currentRevision === 7;
} catch {
  r.notes_module_canonical = false;
}

// --- src/state/vaultState.ts exists and holds entries, gated on api/files ---
try {
  const filesOk = await import(canonUrl("src", "api", "files.ts"))
    .then(() => true)
    .catch(() => false);
  const m = await import(canonUrl("src", "state", "vaultState.ts"));
  const vs = new m.VaultState();
  vs.setRoot("/root");
  vs.setEntries([{ path: "a.md", name: "a", size: 1 }]);
  const held = vs.getEntries();
  vs.clear();
  r.vault_state_canonical =
    filesOk &&
    vs.getRoot() === "/root" &&
    held.length === 1 &&
    vs.getEntries().length === 0;
} catch {
  r.vault_state_canonical = false;
}

// --- src/state/searchState.ts exists and drops stale results on new query ---
try {
  const searchOk = await import(canonUrl("src", "api", "search.ts"))
    .then(() => true)
    .catch(() => false);
  const m = await import(canonUrl("src", "state", "searchState.ts"));
  const ss = new m.SearchState();
  ss.setQuery("alpha");
  ss.setResults([{ id: "a", title: "A", path: "a", snippet: "", score: 1 }]);
  const heldOne = ss.getResults().length === 1;
  ss.setQuery("beta");
  r.search_state_canonical =
    searchOk &&
    heldOne &&
    ss.getQuery() === "beta" &&
    ss.getResults().length === 0;
} catch {
  r.search_state_canonical = false;
}

// --- src/state/settingsState.ts exists and round-trips settings ---
try {
  const settingsOk = await import(canonUrl("src", "api", "settings.ts"))
    .then(() => true)
    .catch(() => false);
  const m = await import(canonUrl("src", "state", "settingsState.ts"));
  const st = new m.SettingsState();
  st.set({ version: 2, theme: "dark", vault_root: "/v" });
  r.settings_state_canonical =
    settingsOk && st.getTheme() === "dark" && st.get().vaultRoot === "/v";
} catch {
  r.settings_state_canonical = false;
}

console.log(JSON.stringify(r));
