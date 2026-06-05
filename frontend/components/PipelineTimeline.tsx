"use client";
import { PIPELINE_STEPS } from "@/lib/format";
import { Check, Circle, Loader2 } from "lucide-react";
import { ProgressEvent } from "@/lib/api";

export function PipelineTimeline({ events }: { events: ProgressEvent[] }) {
  const completed = new Set<string>();
  let current: string | null = null;

  for (const ev of events) {
    if (ev.type === "task_completed" && ev.task_id) completed.add(ev.task_id);
    if (ev.type === "task_started" && ev.task_id) current = ev.task_id;
  }
  // After crew_completed, nothing is "current".
  if (events.some((e) => e.type === "crew_completed" || e.type === "done")) current = null;

  return (
    <ol className="space-y-3">
      {PIPELINE_STEPS.map((step, i) => {
        const isDone = completed.has(step.id);
        const isCurrent = current === step.id;
        return (
          <li key={step.id} className="flex items-start gap-3">
            <div className="mt-0.5">
              {isDone ? (
                <span className="grid h-7 w-7 place-items-center rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  <Check className="h-4 w-4" />
                </span>
              ) : isCurrent ? (
                <span className="grid h-7 w-7 place-items-center rounded-full bg-accent/15 text-accent border border-accent/30">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </span>
              ) : (
                <span className="grid h-7 w-7 place-items-center rounded-full bg-surface2/40 text-muted border border-border">
                  <Circle className="h-3.5 w-3.5" />
                </span>
              )}
            </div>
            <div className="flex-1 pt-0.5">
              <div className={`text-sm ${isDone ? "text-white" : isCurrent ? "text-white" : "text-muted"}`}>
                <span className="text-xs text-muted mr-2">Step {i + 1}</span>
                {step.label}
              </div>
              {isCurrent && (
                <div className="text-xs text-accent mt-0.5 animate-pulse">in progress…</div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
