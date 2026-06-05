export type RunStatus = "pending" | "running" | "completed" | "failed";

export interface RunSummary {
  id: string;
  topic: string;
  status: RunStatus;
  current_step: string;
  progress: number;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface RunDetail extends RunSummary {
  plan: string | null;
  dossier: string | null;
  report: string | null;
  blog: string | null;
  seo: string | null;
  error: string | null;
}

export interface ProgressEvent {
  type:
    | "crew_started"
    | "task_completed"
    | "agent_completed"
    | "crew_completed"
    | "crew_failed"
    | "done"
    | "log"
    | "task_started"
    | "error";
  run_id: string;
  task_id?: string;
  label?: string;
  completed?: string[];
  total?: number;
  message?: string;
  agent_role?: string;
  status?: RunStatus;
  duration_seconds?: number;
  error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => http<{ status: string; version: string; database: string }>("/health"),
  listRuns: (limit = 50) => http<RunSummary[]>(`/runs?limit=${limit}`),
  getRun: (id: string) => http<RunDetail>(`/runs/${id}`),
  deleteRun: (id: string) => http<void>(`/runs/${id}`, { method: "DELETE" }),
  startResearch: (topic: string) =>
    http<{ run_id: string; status: string }>(`/research`, {
      method: "POST",
      body: JSON.stringify({ topic }),
    }),
  streamUrl: (id: string) => `${API_BASE}/research/${id}/stream`,
};
