"use client";
import useSWR from "swr";
import Link from "next/link";
import { api, RunSummary } from "@/lib/api";
import { formatDate, formatDuration, statusPill } from "@/lib/format";
import { Loader2, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";

export default function HistoryPage() {
  const { data, error, isLoading, mutate } = useSWR<RunSummary[]>("runs", () => api.listRuns(100));
  const [deleting, setDeleting] = useState<string | null>(null);

  async function onDelete(id: string) {
    if (!confirm("Delete this run? This cannot be undone.")) return;
    setDeleting(id);
    try { await api.deleteRun(id); mutate(); }
    finally { setDeleting(null); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold">Run history</h1>
          <p className="text-muted text-sm mt-1">All past research runs, newest first.</p>
        </div>
        <Link href="/" className="btn-primary"><Sparkles className="h-4 w-4" /> New research</Link>
      </div>

      {isLoading && (
        <div className="card card-pad flex items-center gap-2 text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}
      {error && <div className="card card-pad text-rose-300">Failed to load runs: {String(error)}</div>}

      {data && data.length === 0 && (
        <div className="card card-pad text-center text-muted py-12">
          No runs yet. <Link href="/" className="text-accent">Start your first research →</Link>
        </div>
      )}

      {data && data.length > 0 && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface2/40 text-muted text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-5 py-3">Topic</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-left px-5 py-3">Step</th>
                <th className="text-left px-5 py-3">Duration</th>
                <th className="text-left px-5 py-3">Created</th>
                <th className="px-5 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => (
                <tr key={r.id} className="border-t border-border/60 hover:bg-surface2/30 transition">
                  <td className="px-5 py-3">
                    <Link href={`/research/${r.id}`} className="text-white hover:text-accent2">{r.topic}</Link>
                    <div className="text-[11px] text-muted">{r.id}</div>
                  </td>
                  <td className="px-5 py-3">
                    <span className={statusPill(r.status)}>
                      {r.status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
                      {r.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-muted">{r.current_step || "—"}</td>
                  <td className="px-5 py-3 text-muted">{formatDuration(r.duration_seconds)}</td>
                  <td className="px-5 py-3 text-muted">{formatDate(r.created_at)}</td>
                  <td className="px-5 py-3 text-right">
                    <button
                      onClick={() => onDelete(r.id)}
                      className="p-1.5 text-muted hover:text-rose-300 transition disabled:opacity-50"
                      disabled={deleting === r.id}
                      title="Delete run"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
