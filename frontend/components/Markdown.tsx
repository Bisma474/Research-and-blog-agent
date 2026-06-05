"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string | null | undefined }) {
  if (!children) return <p className="text-muted text-sm italic">No content yet.</p>;
  return (
    <div className="prose-doc">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
