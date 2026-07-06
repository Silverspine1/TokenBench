// Node harness for VD1. Imports the candidate normalizeSearchResult from the
// workspace under test and reports TS-side canonical-shape checks.
const ws = process.env.TOKENBENCH_WORKSPACE;
if (!ws) {
  console.error("TOKENBENCH_WORKSPACE not set");
  process.exit(2);
}
const url = "file:///" + ws.replace(/\\/g, "/") + "/src/api/search.ts";
const mod = await import(url);
const { normalizeSearchResult } = mod;

const r = {};

// New-shape backend object normalizes to the canonical view.
{
  const v = normalizeSearchResult({
    id: "a",
    title: "Alpha",
    path: "a.md",
    snippet: "hello",
    score: 2,
  });
  r.ts_new_shape_canonical =
    v.id === "a" &&
    v.title === "Alpha" &&
    v.path === "a.md" &&
    v.snippet === "hello" &&
    v.score === 2;
}

// Older-shape backend object still normalizes to the canonical view.
{
  const v = normalizeSearchResult({
    docId: "b",
    name: "Beta",
    location: "b.md",
    preview: "world",
    rank: 3,
  });
  r.ts_old_shape_canonical =
    v.id === "b" &&
    v.title === "Beta" &&
    v.path === "b.md" &&
    v.snippet === "world" &&
    v.score === 3;
}

console.log(JSON.stringify(r));
