"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, RunDetail } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import { formatDate, formatDuration, statusPill } from "@/lib/format";
import { ArrowLeft, Download, FileText, BookOpen, Sparkles } from "lucide-react";

export default function ViewPage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);

  useEffect(() => {
    api.getRun(id as string).then(setRun).catch(() => {});
  }, [id]);

  if (!run) return <div className="text-muted">Loading…</div>;

  function download(name: string, content: string | null) {
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href={`/research/${run.id}`} className="text-xs text-muted hover:text-white inline-flex items-center gap-1">
            <ArrowLeft className="h-3 w-3" /> Back to run
          </Link>
          <h1 className="mt-1 text-2xl md:text-3xl font-semibold">{run.topic}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={statusPill(run.status)}>{run.status}</span>
            <span className="pill">⏱ {formatDuration(run.duration_seconds)}</span>
            <span className="pill">📅 {formatDate(run.created_at)}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => download("report.md", run.report)} className="btn-ghost"><FileText className="h-4 w-4" /> Report</button>
          <button onClick={() => download("blog.md", run.blog)} className="btn-ghost"><BookOpen className="h-4 w-4" /> Blog</button>
        </div>
      </div>

      {run.seo && (
        <div className="card card-pad">
          <div className="flex items-center gap-2 label mb-2"><Sparkles className="h-3.5 w-3.5" /> SEO metadata</div>
          <Markdown>{run.seo}</Markdown>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="card card-pad">
          <div className="label mb-3">Blog post</div>
          <Markdown>{run.blog}</Markdown>
        </div>
        <div className="card card-pad">
          <div className="label mb-3">Final report</div>
          <Markdown>{run.report}</Markdown>
        </div>
      </div>
    </div>
  );
}
