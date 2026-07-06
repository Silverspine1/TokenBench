// Catch-all module left behind by an editor migration. It mixes the file-entry
// surface and the save-result surface that the UI consumes. The pieces here were
// pulled in from several places and dropped together; the grouping does not
// follow the documented module boundaries.

// ---- file entry surface ----

export interface FileEntryView {
  path: string;
  name: string;
  size: number;
}

export interface AppErrorView {
  code: string;
  message: string;
}

export function normalizeFileEntry(raw: any): FileEntryView {
  const r = raw ?? {};
  const size = typeof r.size === "number" ? r.size : Number(r.size) || 0;
  return {
    path: String(r.path ?? ""),
    name: String(r.name ?? ""),
    size,
  };
}

export function normalizeError(raw: any): AppErrorView {
  const r = raw ?? {};
  return {
    code: String(r.code ?? "UNKNOWN"),
    message: String(r.message ?? ""),
  };
}

// ---- save result surface ----

export interface SaveResultView {
  ok: boolean;
  revision: number;
  conflict: boolean;
  currentRevision: number;
}

export function normalizeSaveResult(raw: any): SaveResultView {
  const r = raw ?? {};
  const revision = toNumber(r.revision, 0);
  const currentRevision = toNumber(
    r.currentRevision ?? r.current_revision,
    revision,
  );
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
