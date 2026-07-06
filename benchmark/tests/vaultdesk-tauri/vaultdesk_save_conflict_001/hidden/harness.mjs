// Node harness for VD5. Imports the candidate normalizeSaveResult from the
// workspace under test and reports TS-side canonical-shape checks.
const ws = process.env.TOKENBENCH_WORKSPACE;
if (!ws) {
  console.error("TOKENBENCH_WORKSPACE not set");
  process.exit(2);
}
const url = "file:///" + ws.replace(/\\/g, "/") + "/src/api/notes.ts";
const mod = await import(url);
const { normalizeSaveResult } = mod;

const r = {};

// Current camelCase backend shape normalizes cleanly.
{
  const v = normalizeSaveResult({
    ok: true,
    revision: 2,
    conflict: false,
    currentRevision: 2,
  });
  r.ts_new_shape =
    v.ok === true &&
    v.conflict === false &&
    v.revision === 2 &&
    v.currentRevision === 2;
}

// Older snake_case backend shape still maps currentRevision.
{
  const v = normalizeSaveResult({
    ok: false,
    revision: 1,
    conflict: true,
    current_revision: 7,
  });
  r.ts_snake_shape =
    v.ok === false &&
    v.conflict === true &&
    v.revision === 1 &&
    v.currentRevision === 7;
}

console.log(JSON.stringify(r));
