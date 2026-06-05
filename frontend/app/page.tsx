import { RunForm } from "@/components/RunForm";
import { Sparkles, Bot, Globe, ShieldCheck, FileText, BookOpen, Gauge, Network } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="text-center pt-4">
        <div className="inline-flex items-center gap-2 pill border-accent/30 bg-accent/10 text-accent">
          <Sparkles className="h-3.5 w-3.5" />
          7-agent pipeline · live streaming
        </div>
        <h1 className="mt-4 text-4xl md:text-5xl font-semibold tracking-tight">
          From topic to <span className="bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">published blog</span>
          <br />in minutes, not days.
        </h1>
        <p className="mt-4 text-muted max-w-2xl mx-auto">
          A production multi-agent system that plans, researches, fact-checks, writes,
          edits, and SEO-optimizes long-form content — with a live progress stream.
        </p>
      </section>

      <section className="card card-pad max-w-3xl mx-auto">
        <RunForm />
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto">
        {[
          { icon: Network,    label: "Research planner" },
          { icon: Globe,      label: "Web researcher"   },
          { icon: ShieldCheck,label: "Fact-checker"     },
          { icon: FileText,   label: "Report writer"    },
          { icon: Bot,        label: "Editor"           },
          { icon: BookOpen,   label: "Blog writer"      },
          { icon: Gauge,      label: "SEO specialist"   },
          { icon: Sparkles,   label: "Live SSE stream"  },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="card card-pad flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent/10 text-accent">
              <Icon className="h-4 w-4" />
            </span>
            <span className="text-sm">{label}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
