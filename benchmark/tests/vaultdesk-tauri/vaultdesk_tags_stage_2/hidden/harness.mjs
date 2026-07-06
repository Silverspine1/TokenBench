// Node harness for the Stage 2 saved-search frontend surface. Imports the
// candidate saveSearch / runSavedSearch wrappers and verifies they dispatch to
// the save_search / run_saved_search backend commands and normalize results.
const ws = process.env.TOKENBENCH_WORKSPACE;
if (!ws) {
  console.error("TOKENBENCH_WORKSPACE not set");
  process.exit(2);
}
const url = "file:///" + ws.replace(/\\/g, "/") + "/src/api/savedSearch.ts";
const mod = await import(url);
const { saveSearch, runSavedSearch } = mod;

const r = {};

// saveSearch dispatches to save_search with a normalized {text, tags} query.
{
  let seenCmd = null;
  let seenArgs = null;
  const invoke = (cmd, args) => {
    seenCmd = cmd;
    seenArgs = args;
    return true;
  };
  let ok = false;
  try {
    const accepted = saveSearch(invoke, "combo", { text: "report", tags: ["work"] });
    const q = seenArgs && seenArgs.query;
    ok =
      seenCmd === "save_search" &&
      accepted === true &&
      seenArgs.name === "combo" &&
      q &&
      q.text === "report" &&
      Array.isArray(q.tags) &&
      q.tags.length === 1 &&
      q.tags[0] === "work";
  } catch {
    ok = false;
  }
  r.ts_save_search_wrapper = ok;
}

// runSavedSearch dispatches to run_saved_search and normalizes the result list.
{
  let seenCmd = null;
  let seenArgs = null;
  const invoke = (cmd, args) => {
    seenCmd = cmd;
    seenArgs = args;
    return [
      { id: "n1", title: "One", path: "n1.md", snippet: "s", score: 1 },
      { docId: "n3", name: "Three", location: "n3.md", preview: "p", rank: 2 },
    ];
  };
  let ok = false;
  try {
    const out = runSavedSearch(invoke, "combo");
    ok =
      seenCmd === "run_saved_search" &&
      seenArgs.name === "combo" &&
      out.length === 2 &&
      out[0].id === "n1" &&
      out[1].id === "n3" &&
      out[1].title === "Three";
  } catch {
    ok = false;
  }
  r.ts_run_saved_search_wrapper = ok;
}

console.log(JSON.stringify(r));
