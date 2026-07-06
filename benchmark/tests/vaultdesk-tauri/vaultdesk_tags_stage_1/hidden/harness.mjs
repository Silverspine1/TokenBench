// Node harness for the Stage 1 tagging frontend surface. Imports the candidate
// searchByTag wrapper from the workspace under test and verifies it dispatches
// to the search_by_tag backend command and normalizes results into the
// canonical shape, while leaving the text-search path intact.
const ws = process.env.TOKENBENCH_WORKSPACE;
if (!ws) {
  console.error("TOKENBENCH_WORKSPACE not set");
  process.exit(2);
}
const url = "file:///" + ws.replace(/\\/g, "/") + "/src/api/search.ts";
const mod = await import(url);
const { searchByTag, searchByText } = mod;

const r = {};

// searchByTag dispatches to the search_by_tag command and normalizes results.
{
  let seenCmd = null;
  let seenArgs = null;
  const invoke = (cmd, args) => {
    seenCmd = cmd;
    seenArgs = args;
    return [
      { id: "n1", title: "One", path: "n1.md", snippet: "s", score: 1 },
      { docId: "n2", name: "Two", location: "n2.md", preview: "p", rank: 2 },
    ];
  };
  let ok = false;
  try {
    const out = searchByTag(invoke, "work");
    ok =
      seenCmd === "search_by_tag" &&
      seenArgs &&
      seenArgs.name === "work" &&
      Array.isArray(out) &&
      out.length === 2 &&
      out[0].id === "n1" &&
      out[1].id === "n2" &&
      out[1].title === "Two" &&
      typeof out[0].score === "number";
  } catch {
    ok = false;
  }
  r.ts_search_by_tag_wrapper = ok;
}

// The text-search wrapper is preserved and still dispatches to `search`.
{
  let seenCmd = null;
  const invoke = (cmd) => {
    seenCmd = cmd;
    return [{ id: "a", title: "A", path: "a.md", snippet: "", score: 1 }];
  };
  let ok = false;
  try {
    const out = searchByText(invoke, "needle");
    ok = seenCmd === "search" && out.length === 1 && out[0].id === "a";
  } catch {
    ok = false;
  }
  r.ts_text_search_preserved = ok;
}

console.log(JSON.stringify(r));
