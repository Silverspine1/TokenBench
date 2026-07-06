// Output-stress runner for vaultdesk_revision_stage_2. Simulates a long,
// fully deterministic sequence of save / conflict cycles against an in-memory
// revision history and prints one fixed-width line per cycle. The simulation is
// self-contained and offline: revision ids are monotonic counters, never
// timestamps, so the output is byte-for-byte reproducible. Output lands in the
// 50-300 KB band. Every line reports OK; this exercises no real check.

// Minimal mirror of the revision-checked save semantics, kept local so the
// stress runner is independent of the candidate's exact module layout.
class RevisionSim {
  constructor() {
    this.current = new Map(); // path -> { id, content }
  }
  currentId(path) {
    const e = this.current.get(path);
    return e ? e.id : 0;
  }
  save(path, content, expected, overwrite) {
    const cur = this.currentId(path);
    if (expected !== cur && !overwrite) {
      return { ok: false, revision: cur, conflict: true, currentRevision: cur };
    }
    const next = cur + 1;
    this.current.set(path, { id: next, content });
    return { ok: true, revision: next, conflict: false, currentRevision: next };
  }
}

function pad(n, w) {
  return String(n).padStart(w, "0");
}

const sim = new RevisionSim();
const paths = [];
for (let i = 0; i < 16; i += 1) {
  paths.push("notes/section-" + (i % 4) + "/doc-" + pad(i, 3) + ".md");
}

let line = 0;
let conflicts = 0;
let accepts = 0;

// 1250 cycles: deterministic mix of in-sync saves, stale saves, and forced
// overwrites across a fixed set of note paths.
for (let i = 0; i < 1250; i += 1) {
  const path = paths[i % paths.length];
  const cur = sim.currentId(path);
  // Every third cycle uses a deliberately stale expected revision.
  const stale = i % 3 === 0;
  // Every seventh stale cycle forces an overwrite.
  const overwrite = stale && i % 7 === 0;
  const expected = stale ? (cur > 0 ? cur - 1 : 99) : cur;
  const content = "revision-body-" + pad(i, 5) + "-for-" + path;
  const res = sim.save(path, content, expected, overwrite);
  if (res.conflict) {
    conflicts += 1;
  } else {
    accepts += 1;
  }
  // Predicate that must always hold: a conflict is reported exactly when the
  // expected revision was stale and overwrite was not requested.
  const ok = res.conflict === (stale && !overwrite);
  line += 1;
  console.log(
    "cycle " +
      pad(line, 5) +
      " path=" +
      path +
      " expected=" +
      pad(expected, 3) +
      " overwrite=" +
      (overwrite ? "1" : "0") +
      " ok=" +
      (res.ok ? "1" : "0") +
      " conflict=" +
      (res.conflict ? "1" : "0") +
      " revision=" +
      pad(res.revision, 4) +
      " current=" +
      pad(res.currentRevision, 4) +
      " -> " +
      (ok ? "OK" : "FAIL"),
  );
}

console.log(
  "\nrevision stress complete: " +
    line +
    " cycles, " +
    accepts +
    " accepted, " +
    conflicts +
    " conflicts",
);
process.exit(0);
