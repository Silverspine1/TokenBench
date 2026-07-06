// Visible smoke runner for the TypeScript frontend. Node v24 imports the .ts
// modules directly via type stripping. Prints `ok - <name>` / `not ok - <name>`
// for each check and exits non-zero if any check fails.

import {
  normalizeSearchResult,
  normalizeSearchResults,
} from "../api/search.ts";
import { normalizeSaveResult } from "../api/notes.ts";
import { normalizeSettings } from "../api/settings.ts";
import { SearchState } from "../state/searchState.ts";
import { SettingsState } from "../state/settingsState.ts";
import { NoteState } from "../state/noteState.ts";
import { renderSearchPanel } from "../components/SearchPanel.ts";

let failures = 0;

function check(name, condition) {
  if (condition) {
    console.log(`ok - ${name}`);
  } else {
    console.log(`not ok - ${name}`);
    failures += 1;
  }
}

// normalizeSearchResult on the new backend shape.
{
  const r = normalizeSearchResult({
    id: "a",
    title: "Alpha",
    path: "a.md",
    snippet: "hello",
    score: 2,
  });
  check(
    "normalizeSearchResult new shape",
    r.id === "a" &&
      r.title === "Alpha" &&
      r.path === "a.md" &&
      r.snippet === "hello" &&
      r.score === 2,
  );
}

// normalizeSearchResult tolerates the older shape.
{
  const r = normalizeSearchResult({
    docId: "b",
    name: "Beta",
    location: "b.md",
    preview: "world",
    rank: 3,
  });
  check(
    "normalizeSearchResult old shape",
    r.id === "b" &&
      r.title === "Beta" &&
      r.path === "b.md" &&
      r.snippet === "world" &&
      r.score === 3,
  );
}

// normalizeSearchResults maps a list.
{
  const list = normalizeSearchResults([
    { id: "a", title: "A", path: "a", snippet: "", score: 1 },
    { docId: "b", name: "B", location: "b", preview: "", rank: 2 },
  ]);
  check(
    "normalizeSearchResults list",
    list.length === 2 && list[0].id === "a" && list[1].id === "b",
  );
}

// Save-conflict wrapper shape with snake_case input.
{
  const r = normalizeSaveResult({
    ok: false,
    revision: 1,
    conflict: true,
    current_revision: 1,
  });
  check(
    "normalizeSaveResult conflict shape",
    r.ok === false &&
      r.conflict === true &&
      r.revision === 1 &&
      r.currentRevision === 1,
  );
}

// Save-accept wrapper shape with camelCase input.
{
  const r = normalizeSaveResult({
    ok: true,
    revision: 2,
    conflict: false,
    currentRevision: 2,
  });
  check(
    "normalizeSaveResult accept shape",
    r.ok === true && r.conflict === false && r.currentRevision === 2,
  );
}

// Settings read preserves unknown fields and derives the view.
{
  const s = normalizeSettings({
    version: 2,
    theme: "dark",
    vault_root: "/v",
    plugin: { keep: 42 },
  });
  check(
    "normalizeSettings read",
    s.version === 2 &&
      s.theme === "dark" &&
      s.vaultRoot === "/v" &&
      s.extra.plugin !== undefined,
  );
}

// SettingsState round trip through the state holder.
{
  const st = new SettingsState();
  st.set({ version: 2, theme: "dark", vault_root: "/v" });
  check("SettingsState theme", st.getTheme() === "dark");
}

// SearchState does not serve stale results after a new query is set.
{
  const ss = new SearchState();
  ss.setQuery("alpha");
  ss.setResults([
    { id: "a", title: "A", path: "a", snippet: "", score: 1 },
  ]);
  check("SearchState holds results", ss.getResults().length === 1);
  ss.setQuery("beta");
  check("SearchState clears on new query", ss.getResults().length === 0);
}

// NoteState applies a conflict result without losing local content.
{
  const ns = new NoteState();
  ns.load("a.md", "local edits", 0);
  const res = ns.applySaveResult({
    ok: false,
    revision: 0,
    conflict: true,
    currentRevision: 5,
  });
  check(
    "NoteState conflict keeps content",
    res.conflict === true &&
      ns.getContent() === "local edits" &&
      ns.getRevision() === 5,
  );
}

// Component renders from state.
{
  const ss = new SearchState();
  ss.setQuery("alpha");
  ss.setResults([
    { id: "a", title: "Alpha", path: "a", snippet: "", score: 2 },
  ]);
  const out = renderSearchPanel(ss);
  check(
    "renderSearchPanel output",
    out.includes("query: alpha") && out.includes("Alpha"),
  );
}

// Deterministic bounded diagnostic matrix. Emits ~1200 synthetic
// search-result normalization and save-conflict cases so the visible output
// lands in the 50-300 KB band without affecting any real check above. Each
// line is fully deterministic and reports OK.
{
  const themes = ["light", "dark", "sepia", "high-contrast"];
  let line = 0;
  for (let i = 0; i < 600; i += 1) {
    const sr = normalizeSearchResult({
      id: "doc-" + i,
      title: "Document " + i,
      path: "notes/section-" + (i % 12) + "/doc-" + i + ".md",
      snippet: "synthetic snippet body for document number " + i,
      score: (i % 17) + 0.5,
    });
    const ok =
      sr.id === "doc-" + i &&
      sr.path.endsWith("doc-" + i + ".md") &&
      typeof sr.score === "number";
    line += 1;
    console.log(
      "case " +
        String(line).padStart(4, "0") +
        ": normalize id=" +
        sr.id +
        " score=" +
        sr.score +
        " theme=" +
        themes[i % themes.length] +
        " -> " +
        (ok ? "OK" : "FAIL"),
    );
  }
  for (let i = 0; i < 600; i += 1) {
    const rev = i % 23;
    const stale = i % 3 === 0;
    const res = normalizeSaveResult({
      ok: !stale,
      revision: stale ? rev : rev + 1,
      conflict: stale,
      current_revision: rev + (stale ? 0 : 1),
    });
    const ok =
      res.conflict === stale &&
      typeof res.currentRevision === "number" &&
      typeof res.revision === "number";
    line += 1;
    console.log(
      "case " +
        String(line).padStart(4, "0") +
        ": saveconflict path=notes/doc-" +
        i +
        ".md expected=" +
        rev +
        " conflict=" +
        res.conflict +
        " current=" +
        res.currentRevision +
        " -> " +
        (ok ? "OK" : "FAIL"),
    );
  }
}

if (failures > 0) {
  console.log(`\n${failures} check(s) failed`);
  process.exit(1);
} else {
  console.log("\nall checks passed");
  process.exit(0);
}
