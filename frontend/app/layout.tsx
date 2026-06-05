import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Research & Blog Crew",
  description: "Production-grade multi-agent research and blog platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/70 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-accent to-accent2 text-white font-bold">R</span>
              <div>
                <div className="text-sm font-semibold leading-tight">Research &amp; Blog Crew</div>
                <div className="text-[11px] text-muted leading-tight">7-agent pipeline · powered by CrewAI</div>
              </div>
            </Link>
            <nav className="flex items-center gap-2">
              <Link href="/history" className="btn-ghost text-sm">History</Link>
              <Link href="/" className="btn-primary text-sm">New research</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-10 text-center text-xs text-muted">
          Built with Next.js · FastAPI · CrewAI · Tailwind
        </footer>
      </body>
    </html>
  );
}
