// Canonical file-entry shape consumed by the UI.
export interface FileEntryView {
  path: string;
  name: string;
  size: number;
}

// Canonical normalized error shape read from the backend.
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
