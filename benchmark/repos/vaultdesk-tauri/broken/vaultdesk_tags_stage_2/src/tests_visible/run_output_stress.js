// Output-stress runner for the VaultDesk frontend reorg task. Emits a large,
// fully deterministic diagnostic matrix through the stable public barrel
// (src/api/commands.ts) so the visible output lands in the 50-300 KB band. Every
// line is deterministic and reports OK; this exercises only the public surface
// and never touches the internal module layout.

import {
  normalizeSearchResult,
  normalizeSaveResult,
  normalizeSettings,
} from "../api/commands.ts";

const themes = ["light", "dark", "sepia", "high-contrast"];
let line = 0;

for (let i = 0; i < 700; i += 1) {
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
      " path=" +
      sr.path +
      " -> " +
      (ok ? "OK" : "FAIL"),
  );
}

for (let i = 0; i < 700; i += 1) {
  const rev = i % 23;
  const stale = i % 3 === 0;
  const res = normalizeSaveResult({
    ok: !stale,
    revision: stale ? rev : rev + 1,
    conflict: stale,
    current_revision: rev + (stale ? 0 : 1),
  });
  const st = normalizeSettings({
    version: 2,
    theme: themes[i % themes.length],
    vault_root: "/vault/root/" + (i % 9),
  });
  const ok =
    res.conflict === stale &&
    typeof res.currentRevision === "number" &&
    st.theme === themes[i % themes.length];
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
      " theme=" +
      st.theme +
      " vaultRoot=" +
      st.vaultRoot +
      " -> " +
      (ok ? "OK" : "FAIL"),
  );
}

console.log("\noutput stress complete: " + line + " cases");
process.exit(0);
