"use client";
import { useEffect, useRef, useState } from "react";
import { api, ProgressEvent } from "@/lib/api";

export function useRunStream(runId: string | null) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<string>("connecting");
  const [done, setDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!runId) return;
    const es = new EventSource(api.streamUrl(runId));
    esRef.current = es;
    setStatus("connecting");
    setEvents([]);
    setDone(false);

    es.onopen = () => setStatus("connected");
    es.onerror = () => setStatus((s) => (s === "connected" ? s : "reconnecting"));

    es.onmessage = (msg) => {
      try {
        const ev: ProgressEvent = JSON.parse(msg.data);
        setEvents((prev) => [...prev, ev]);
        if (ev.type === "done") {
          setDone(true);
          if (ev.status) setStatus(ev.status);
          es.close();
        }
        if (ev.type === "crew_failed") {
          setStatus("failed");
        }
      } catch { /* ignore */ }
    };

    return () => { es.close(); esRef.current = null; };
  }, [runId]);

  return { events, status, done };
}
