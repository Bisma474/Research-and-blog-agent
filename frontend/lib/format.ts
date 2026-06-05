import clsx, { ClassValue } from "clsx";
import type { RunStatus } from "./api";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

export function statusPill(status: RunStatus) {
  switch (status) {
    case "running":   return "pill-running";
    case "completed": return "pill-done";
    case "failed":    return "pill-failed";
    default:          return "pill-pending";
  }
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds == null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch { return iso; }
}

export const PIPELINE_STEPS = [
  { id: "planning_task",      label: "Planning research",      icon: "Map" },
  { id: "research_task",      label: "Web research",           icon: "Search" },
  { id: "fact_check_task",    label: "Fact-checking",          icon: "ShieldCheck" },
  { id: "report_task",        label: "Writing report",         icon: "FileText" },
  { id: "editing_task",       label: "Editing report",         icon: "Pencil" },
  { id: "blog_writing_task",  label: "Writing blog post",      icon: "BookOpen" },
  { id: "seo_task",           label: "Generating SEO metadata", icon: "Sparkles" },
];
