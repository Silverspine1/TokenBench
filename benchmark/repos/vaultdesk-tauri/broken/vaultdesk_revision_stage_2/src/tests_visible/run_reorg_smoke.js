// Reorg smoke runner for the VaultDesk frontend. Exercises ONLY the stable
// public barrel (src/api/commands.ts), so it runs regardless of how the
// underlying modules are laid out. Node v24 imports the .ts barrel directly via
// type stripping. Prints `ok - <name>` / `not ok - <name>` and exits non-zero on
// any failure.

import {
  normalizeSearchResult,
  normalizeSearchResults,
  normalizeSettings,
  normalizeSaveResult,
  normalizeFileEntry,
  VaultState,
  SearchState,
  SettingsState,
  NoteState,
} from "../api/commands.ts";

let failures = 0;

function check(name, condition) {
  if (condition) {
    console.log(`ok - ${name}`);
  } else {
    console.log(`not ok - ${name}`);
    failures += 1;
  }
}

// search normalization through the barrel.
{
  const r = normalizeSearchResult({
    docId: "b",
    name: "Beta",
    location: "b.md",
    preview: "world",
    rank: 3,
  });
  check(
    "barrel normalizeSearchResult old shape",
    r.id === "b" && r.title === "Beta" && r.snippet === "world" && r.score === 3,
  );
  const list = normalizeSearchResults([
    { id: "a", title: "A", path: "a", snippet: "", score: 1 },
  ]);
  check("barrel normalizeSearchResults list", list.length === 1);
}

// settings normalization through the barrel.
{
  const s = normalizeSettings({ version: 2, theme: "dark", vault_root: "/v" });
  check("barrel normalizeSettings", s.theme === "dark" && s.vaultRoot === "/v");
}

// save-result + file-entry normalization through the barrel.
{
  const sr = normalizeSaveResult({
    ok: false,
    revision: 1,
    conflict: true,
    current_revision: 7,
  });
  check(
    "barrel normalizeSaveResult conflict",
    sr.conflict === true && sr.currentRevision === 7,
  );
  const fe = normalizeFileEntry({ path: "a.md", name: "a", size: "12" });
  check("barrel normalizeFileEntry", fe.size === 12 && fe.path === "a.md");
}

// state holders through the barrel.
{
  const ss = new SearchState();
  ss.setQuery("alpha");
  ss.setResults([{ id: "a", title: "A", path: "a", snippet: "", score: 1 }]);
  check("barrel SearchState holds", ss.getResults().length === 1);
  ss.setQuery("beta");
  check("barrel SearchState clears on new query", ss.getResults().length === 0);

  const st = new SettingsState();
  st.set({ version: 2, theme: "dark", vault_root: "/v" });
  check("barrel SettingsState theme", st.getTheme() === "dark");

  const vs = new VaultState();
  vs.setEntries([{ path: "a.md", name: "a", size: 1 }]);
  check("barrel VaultState entries", vs.getEntries().length === 1);

  const ns = new NoteState();
  ns.load("a.md", "local edits", 0);
  ns.applySaveResult({ ok: false, revision: 0, conflict: true, currentRevision: 5 });
  check(
    "barrel NoteState conflict keeps content",
    ns.getContent() === "local edits" && ns.getRevision() === 5,
  );
}

if (failures > 0) {
  console.log(`\n${failures} check(s) failed`);
  process.exit(1);
} else {
  console.log("\nall checks passed");
  process.exit(0);
}
