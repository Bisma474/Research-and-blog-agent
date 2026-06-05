# Research & Blog Crew

> **Production-grade multi-agent system that turns a topic into a research dossier, a long-form report, and a publish-ready blog post — with a live progress stream and full run history.**

A 7-agent [CrewAI](https://crewai.com) pipeline behind a FastAPI service and a Next.js UI. Built to be dropped into a portfolio, a CV, or a production environment with zero extra glue code.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOUR_USERNAME/research_and_blog_crew)

---

## Highlights

- **7 specialized agents** in a sequential, dependency-aware pipeline (planner → researcher → fact-checker → writer → editor → blog writer → SEO).
- **Web-grounded research** via Serper + ScrapeWebsite, plus two custom CrewAI tools (citation formatter, word-count validator).
- **Real-time progress** streamed to the browser over Server-Sent Events (SSE) using CrewAI's event bus.
- **Persistent run history** in SQLite (via SQLModel) with per-step artifact persistence.
- **Polished Next.js 14 dashboard** (App Router + Tailwind + lucide icons) — no build step required to run.
- **Production touches**: structured logging, health endpoint, CORS, error capture, Docker + Compose, automated tests, OpenAPI docs.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Next.js 14 (port 3000)                    │
│  Home (form)   Research/[id] (live SSE)   History   Detail / View    │
└──────────────────┬───────────────────────────────────────────────────┘
                   │  fetch + EventSource
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       FastAPI service (port 8000)                    │
│  /api/v1/health   /api/v1/research (POST + SSE)   /api/v1/runs      │
│                       │                                             │
│                       ▼                                             │
│            CrewRunner (background thread)                            │
│              │   subscribes to CrewAI events                        │
│              ▼                                                     │
│      ┌──────────────────────────────────────────┐                   │
│      │   7-agent CrewAI pipeline (sequential)   │                   │
│      │   1. Research planner                    │                   │
│      │   2. Senior researcher  (web tools)      │                   │
│      │   3. Fact-checker                        │                   │
│      │   4. Report writer                       │                   │
│      │   5. Editor                              │                   │
│      │   6. Blog writer                         │                   │
│      │   7. SEO specialist                      │                   │
│      └──────────────────────────────────────────┘                   │
│                       │                                             │
│                       ▼                                             │
│        SQLite (runs.db)  +  ./output/{run_id}/                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Quick start

### 1. Configure secrets

```bash
cp .env.example .env
# Edit .env and set at least:
#   GROQ_API_KEY=...   (or OPENAI_API_KEY=...)
#   SERPER_API_KEY=... (optional but recommended for web research)
```

### 2. Run the API

```bash
uv sync
uv run uvicorn api.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> for the interactive OpenAPI explorer.

### 3. Run the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open <http://localhost:3000>.

### 4. Or run both with Docker

```bash
docker compose up --build
```

API on `:8000`, UI on `:3000`.

### 5. Or deploy to Render (free, public URL)

The fastest path to a permanent public link for your resume.

1. **Push this repo to GitHub** (create a new public repo, then):
   ```bash
   git init
   git add .
   git commit -m "Initial commit: research & blog crew"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. **Go to [dashboard.render.com](https://dashboard.render.com) → New + → Blueprint**.
3. **Connect your GitHub repo**. Render will detect `render.yaml` and create two services:
   - `research-blog-api` (FastAPI on Python 3.12, persistent disk for SQLite)
   - `research-blog-ui` (Next.js on Node 20, points at the API)
4. **Set the secret env vars** when prompted:
   - `GROQ_API_KEY` — required (or set `OPENAI_API_KEY` + change `MODEL=openai/gpt-4o-mini`)
   - `SERPER_API_KEY` — optional, enables web search
5. **Wait ~5 min** for the first deploy.
6. **Your public UI**: `https://research-blog-ui.onrender.com` — share this on your resume.

Free-tier notes:
- Services sleep after 15 min of inactivity. The first request after sleep takes ~30 s to wake.
- The API has a 1 GB persistent disk mounted at `/var/data` so run history survives redeploys.
- The free plan gives 750 hours/month per service, more than enough for a portfolio demo.

---

## API surface

| Method | Path                                  | Description                              |
|--------|---------------------------------------|------------------------------------------|
| GET    | `/api/v1/health`                      | Liveness + DB check                      |
| POST   | `/api/v1/research`                    | Kick off a new run (returns `run_id`)    |
| GET    | `/api/v1/research/{run_id}/stream`    | SSE stream of progress events            |
| GET    | `/api/v1/runs`                        | List runs (newest first)                 |
| GET    | `/api/v1/runs/{run_id}`               | Full run detail (incl. all artifacts)    |
| DELETE | `/api/v1/runs/{run_id}`               | Delete a run                             |

### SSE event types

`crew_started` · `task_completed` · `agent_completed` · `crew_completed` · `crew_failed` · `done`

Each `task_completed` event includes the artifact inline in the persisted `Run` row, so the UI can render partial progress as it arrives.

---

## Project layout

```
research_and_blog_crew/
├── src/
│   ├── research_and_blog_crew/        # CrewAI package
│   │   ├── crew.py                    # @CrewBase 7-agent orchestration
│   │   ├── config/
│   │   │   ├── agents.yaml            # Role, goal, backstory per agent
│   │   │   └── tasks.yaml             # Task descriptions + expected output
│   │   └── tools/
│   │       └── custom_tool.py         # CitationFormatterTool, WordCountValidatorTool
│   └── api/                           # FastAPI service
│       ├── main.py                    # App factory + startup hooks
│       ├── config.py                  # Pydantic settings
│       ├── database.py                # SQLModel engine (lazy, test-injectable)
│       ├── models.py                  # Run table
│       ├── schemas.py                 # Request/response models
│       ├── routes/
│       │   ├── research.py            # POST /research + SSE stream
│       │   └── runs.py                # CRUD for run history
│       └── services/
│           └── crew_runner.py         # CrewAI event listener + thread runner
├── frontend/                          # Next.js 14 + Tailwind
│   ├── app/
│   │   ├── page.tsx                   # Topic form + suggestions
│   │   ├── research/[id]/page.tsx     # Live progress + tabs
│   │   ├── research/[id]/view/...     # Final blog + report
│   │   └── history/page.tsx           # Run history table
│   ├── components/                    # RunForm, PipelineTimeline, Markdown, ...
│   └── lib/                           # API client, SSE hook, formatters
├── tests/                             # pytest: crew + API smoke tests
├── Dockerfile.api                     # Production API image
├── docker-compose.yml                 # API + frontend
└── pyproject.toml
```

---

## Testing

```bash
uv run pytest          # 9 tests, all green
```

Tests cover:
- CrewAI crew structure (7 agents, 7 tasks, sequential process)
- API health, validation, CRUD, 404 handling
- OpenAPI schema exposure

---

## Configuration reference

| Variable             | Default              | Description                                |
|----------------------|----------------------|--------------------------------------------|
| `MODEL`              | `groq/llama-3.3-70b-versatile` | Default LLM for the crew          |
| `RESEARCHER_LLM`     | inherits `MODEL`     | LLM override for the senior researcher     |
| `PLANNER_LLM`        | inherits `MODEL`     | LLM override for the planner               |
| `WRITER_LLM`         | inherits `MODEL`     | LLM override for the writers               |
| `GROQ_API_KEY`       | —                    | Groq API key (default provider)            |
| `OPENAI_API_KEY`     | —                    | OpenAI API key (set `MODEL=openai/...`)    |
| `ANTHROPIC_API_KEY`  | —                    | Anthropic API key                          |
| `SERPER_API_KEY`     | —                    | Enables web search (free tier at serper.dev) |
| `DATABASE_URL`       | `sqlite:///./runs.db`| SQLModel / SQLAlchemy database URL         |
| `OUTPUT_DIR`         | `./output`           | Where per-run markdown files are written   |

---

## Design decisions

- **Sequential process with `context` chaining.** Each task explicitly depends on the previous one, so the fact-checker sees the dossier, the editor sees the report, and the blog writer sees the final report.
- **Event-bus-driven SSE.** A custom `BaseEventListener` subscribes to `TaskCompletedEvent` / `CrewKickoffCompletedEvent` and pushes progress onto a per-run queue, which the SSE endpoint drains.
- **Lazy DB engine.** `get_engine()` is called on first use, so tests can override `DATABASE_URL` before any table is created.
- **Artifacts persisted incrementally.** Each completed task updates the matching `Run` column so the UI can render partial output (plan, then dossier, then report…) without waiting for the whole crew.
- **Custom tools are real, not stubs.** `CitationFormatterTool` and `WordCountValidatorTool` give the agents deterministic helpers the LLM can't replicate reliably.

---

## Roadmap

- [ ] Hierarchical process option (manager agent delegates)
- [ ] Persist token usage + cost per run
- [ ] RAG knowledge source from `./knowledge/`
- [ ] Export to Markdown / Notion / WordPress
- [ ] Auth (API key + JWT)
- [ ] Vector memory across runs

---

## License

MIT
