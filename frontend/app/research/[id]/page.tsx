"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, RunDetail, ProgressEvent } from "@/lib/api";
import { useRunStream } from "@/lib/useRunStream";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { Markdown } from "@/components/Markdown";
import { formatDuration, statusPill } from "@/lib/format";
import { AlertCircle, ArrowRight, Loader2, RefreshCw, Sparkles } from "lucide-react";

type Tab = "plan" | "dossier" | "report" | "blog" | "seo";

const TABS: { id: Tab; label: string }[] = [
  { id: "plan",    label: "Plan" },
  { id: "dossier", label: "Research" },
  { id: "report",  label: "Report" },
  { id: "blog",    label: "Blog" },
  { id: "seo",     label: "SEO" },
];

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [tab, setTab] = useState<Tab>("plan");
  const [pollError, setPollError] = useState<string | null>(null);

  const { events, status, done } = useRunStream(id as string);

  // Poll the run detail so we can show artifacts as they land.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await api.getRun(id as string);
        if (!cancelled) setRun(r);
        setPollError(null);
      } catch (e: any) { setPollError(e?.message || "Failed to load"); }
    }
    load();
    if (!done) {
      const t = setInterval(load, 3000);
      return () => { cancelled = true; clearInterval(t); };
    }
    load();
    return () => { cancelled = true; };
  }, [id, done, events.length]);

  if (pollError && !run) {
    return <div className="card card-pad text-rose-300">Error: {pollError}</div>;
  }
  if (!run) {
    return <div className="card card-pad flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Loading run…</div>;
  }

  const content = {
    plan:    run.plan,
    dossier: run.dossier,
    report:  run.report,
    blog:    run.blog,
    seo:     run.seo,
  }[tab];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/history" className="text-xs text-muted hover:text-white">← Back to history</Link>
          <h1 className="mt-1 text-2xl md:text-3xl font-semibold">{run.topic}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={statusPill(run.status)}>
              {run.status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
              {run.status}
            </span>
            <span className="pill">⏱ {formatDuration(run.duration_seconds)}</span>
            <span className="pill">📋 {run.current_step || "—"}</span>
            <span className="pill">id: {run.id}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={() => router.push("/")} className="btn-ghost"><Sparkles className="h-4 w-4" /> New</button>
          <Link href={`/research/${run.id}`} className="btn-ghost"><RefreshCw className="h-4 w-4" /> Refresh</Link>
        </div>
      </div>

      {/* Progress bar */}
      <div className="card card-pad">
        <div className="flex items-center justify-between text-sm">
          <div className="label">Pipeline progress</div>
          <div className="text-muted">{run.progress}%</div>
        </div>
        <div className="mt-3 h-2 w-full rounded-full bg-surface2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-accent2 transition-all duration-700"
            style={{ width: `${run.progress}%` }}
          />
        </div>
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-6">
        <aside className="card card-pad h-fit">
          <div className="label mb-4">Agents</div>
          <PipelineTimeline events={events} />
          {run.status === "failed" && run.error && (
            <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
              <div className="flex items-center gap-1.5 font-semibold mb-1">
                <AlertCircle className="h-3.5 w-3.5" /> Crew failed
              </div>
              <pre className="whitespace-pre-wrap break-words text-rose-200/80">{run.error.slice(0, 600)}</pre>
            </div>
          )}
          {done && run.status === "completed" && (
            <Link href={`/research/${run.id}/view`} className="mt-4 btn-primary w-full">
              View final blog <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </aside>

        <section className="card card-pad">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div className="flex flex-wrap gap-1.5">
              {TABS.map((t) => {
                const hasContent = !!content && t.id === tab;
                const isEmpty = !(t.id === "plan" ? run.plan :
                                  t.id === "dossier" ? run.dossier :
                                  t.id === "report" ? run.report :
                                  t.id === "blog" ? run.blog : run.seo);
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={
                      "px-3 py-1.5 rounded-lg text-sm border transition " +
                      (tab === t.id
                        ? "border-accent/40 bg-accent/10 text-white"
                        : "border-border bg-surface2/30 text-muted hover:text-white")
                    }
                  >
                    {t.label}
                    {isEmpty && <span className="ml-2 text-[10px] text-muted">pending</span>}
                  </button>
                );
              })}
            </div>
            <div className="text-xs text-muted">stream: {status}</div>
          </div>
          <div className="max-h-[70vh] overflow-y-auto pr-1">
            <Markdown>{content || ""}</Markdown>
          </div>
        </section>
      </div>

      {/* Raw event log */}
      <details className="card card-pad">
        <summary className="cursor-pointer text-sm text-muted">Raw event log ({events.length})</summary>
        <pre className="mt-3 max-h-80 overflow-auto text-[11px] leading-snug text-zinc-400 bg-surface2/40 rounded-lg p-3">
{events.map((e, i) => `${String(i).padStart(3, "0")}  ${e.type.padEnd(20)} ${JSON.stringify(e).slice(0, 220)}`).join("\n")}
        </pre>
      </details>
    </div>
  );
}
