// Canonical save-result shape consumed by the UI.
export interface SaveResultView {
  ok: boolean;
  revision: number;
  conflict: boolean;
  currentRevision: number;
}

// Map a raw backend save result into the canonical shape. Both the camelCase
// backend shape (currentRevision) and an older snake_case shape
// (current_revision) are tolerated.
export function normalizeSaveResult(raw: any): SaveResultView {
  const r = raw ?? {};
  const revision = toNumber(r.revision, 0);
  const currentRevision = toNumber(r.currentRevision, revision);
  return {
    ok: Boolean(r.ok),
    revision,
    conflict: Boolean(r.conflict),
    currentRevision,
  };
}

function toNumber(value: any, fallback: number): number {
  if (typeof value === "number") {
    return value;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}
