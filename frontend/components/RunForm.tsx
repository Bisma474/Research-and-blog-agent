"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ArrowRight, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "AI Agents in 2026",
  "The state of quantum computing",
  "Retrieval-augmented generation in production",
  "CrewAI vs LangGraph vs AutoGen",
  "The economics of LLM inference",
];

export function RunForm() {
  const router = useRouter();
  const [topic, setTopic] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    const t = topic.trim();
    if (t.length < 2) { setError("Topic must be at least 2 characters."); return; }
    setError(null); setSubmitting(true);
    try {
      const { run_id } = await api.startResearch(t);
      router.push(`/research/${run_id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to start research");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label htmlFor="topic" className="label">Research topic</label>
        <input
          ref={inputRef}
          id="topic"
          className="input mt-2"
          placeholder="e.g. The rise of small language models"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={submitting}
        />
        {error && <div className="mt-2 text-sm text-rose-300">{error}</div>}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setTopic(s)}
              className="pill hover:bg-surface2 hover:text-white transition"
            >
              {s}
            </button>
          ))}
        </div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          <Sparkles className="h-4 w-4" />
          {submitting ? "Starting…" : "Start research"}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </form>
  );
}
