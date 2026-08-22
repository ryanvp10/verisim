# Verisim — Product Spec

> Tagline: **Research receipts for fiction writers.**

Verisim is an AI research desk for screenwriters. It turns a writer's real-world questions ("How does a police interrogation actually work in Tokyo?") into cited research dossiers in seconds, powered by Gemini agents on Google Cloud and live web search from Parallel.

---

## 1. Problem

Screenwriters spend hours or days verifying real-world facts (procedures, places, eras, technical details) so scripts feel authentic. Generic LLM answers hallucinate; search engines return links, not synthesized answers with sources.

## 2. Solution

- Writer creates a **project** (a script) and asks research questions in plain language
- A Gemini agent (ADK) plans searches, calls **Parallel Search API** live, extracts page content when needed
- Result: a structured **dossier** — direct answer, key findings, detailed notes, numbered source citations
- Dossiers are saved per project, support follow-up Q&A threads, and export to Markdown

## 3. Core Flow

```
Writer ──question──▶ Verisim Agent (Gemini/ADK)
                         │ plans & iterates
                         ▼
                  Parallel Search API ──▶ live web results (URLs + excerpts)
                         │ (optional)
                  Parallel Extract ──▶ full page content
                         ▼
                  Synthesis w/ numbered citations
                         ▼
Writer ◀──dossier (answer · findings · notes · sources)── saved to project
```

## 4. Architecture

```
┌──────────────────┐        ┌───────────────────────────────┐
│  Web (React)     │  HTTP  │  Agent API (Python/FastAPI)   │
│  Vite + Tailwind ├───────▶│  google-adk + Gemini (Vertex) │
│  Netlify         │        │  parallel-web SDK (Search/    │
└──────────────────┘        │  Extract) as agent tools      │
                            │  Cloud Run                    │
                            └──────────┬────────────────────┘
                                       │
                            ┌──────────▼────────────────────┐
                            │  Firestore (projects,         │
                            │  dossiers, threads)           │
                            └───────────────────────────────┘
```

## 5. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + Vite + Tailwind | Team's proven stack |
| Agent | Python, **google-adk**, Gemini (Vertex AI) | Hackathon requires Google AI SDK called at runtime; ADK = Agent Builder-native |
| Search | **parallel-web** SDK (Search + Extract API) | Track requirement: partner service used at runtime |
| API | FastAPI | Async-friendly, pairs with ADK tooling |
| DB | Firestore | Serverless, free tier, GCP-native |
| Hosting | Netlify (web) + Cloud Run (API) | Hosted URL requirement; free tiers |

## 6. Project Structure

```
verisim/
├── web/                        # React frontend
│   ├── src/
│   │   ├── main.jsx            # entry
│   │   ├── App.jsx             # router: projects list ↔ project detail
│   │   ├── api.js              # fetch wrapper for agent API
│   │   ├── pages/
│   │   │   ├── ProjectsPage.jsx    # project grid + create dialog
│   │   │   └── ProjectPage.jsx     # dossier list + ask box + thread view
│   │   └── components/
│   │       ├── DossierCard.jsx # summary card w/ source count
│   │       ├── DossierView.jsx # full dossier + clickable citations [n]
│   │       └── ThreadPanel.jsx # follow-up Q&A
├── agent/                      # Python backend
│   ├── main.py                 # FastAPI app + routes
│   ├── agent.py                # ADK agent definition (Gemini + tools)
│   ├── tools.py                # parallel_search(), parallel_extract()
│   ├── db.py                   # Firestore access layer
│   ├── schemas.py              # Pydantic models
│   └── requirements.txt
├── SPEC.md                     # this file
└── README.md                   # judge-facing docs (later task)
```

## 7. API Reference

### POST `/api/projects`
```json
// req  { "title": "Night Ferry", "logline": "...", "genre": "thriller" }
// res  { "id": "abc123", "title": "Night Ferry", "created_at": "..." }
```

### GET `/api/projects` → `[ { id, title, logline, genre, dossier_count } ]`

### POST `/api/projects/{id}/research`
```json
// req  { "question": "Tokyo police interrogation procedure, late 90s" }
// res  {
//   "dossier_id": "d789",
//   "status": "done",
//   "answer": "Suspects are held ... [1][2]",
//   "findings": ["Interrogation is ... ", "..."],
//   "notes": ["Detail: holding period up to 23 days under ..."],
//   "sources": [
//     {"n": 1, "title": "...", "url": "https://...", "excerpt": "..."}
//   ]
// }
```

### GET `/api/projects/{id}/dossiers` → list (newest first)

### GET `/api/dossiers/{dossier_id}` → full dossier

### POST `/api/dossiers/{dossier_id}/thread`
```json
// req  { "message": "What did they eat in holding?" }
// res  { "reply": "... [3]", "sources_added": [...], "messages": [...] }
```

### GET `/api/dossiers/{dossier_id}/export` → Markdown download

Errors: `{ "error": { "code": "invalid_request", "message": "..." } }`, HTTP 400/404/429/500.

## 8. Data Model (Firestore)

```
projects/{projectId}
  title, logline, genre, created_at
  dossiers/{dossierId}
    question, answer, findings[], notes[], sources[{n,title,url,excerpt}],
    status, created_at
    thread/{msgId}: role(user|agent), text, sources_used[], created_at
```

## 9. Frontend

```
App
├── ProjectsPage      (grid of project cards, "+ New Project")
└── ProjectPage
    ├── header (title, logline, edit)
    ├── AskBox        (question input, "Research" button, loading state)
    ├── DossierList   (DossierCard[])
    └── DossierView   (sections + inline citation chips → source drawer)
        └── ThreadPanel (chat bubbles, sources used per reply)
```

- Theme: dark studio aesthetic, warm paper-white dossier panels; serif headings (writing-tool feel)
- Citations render as superscript chips `[n]`; click opens source drawer with excerpt + link
- Mobile-first responsive (user preference: no horizontal scroll; wrap long words)

## 10. Deployment

- **Web:** Netlify, `VITE_API_URL` set in Netlify UI
- **Agent API:** Cloud Run (Dockerfile, min-instances 0), secrets via Cloud Secret Manager (`PARALLEL_API_KEY`, Vertex ADC)
- **Firestore:** native mode, region `asia-southeast2` (or nearest free region)
- Phase 1 (MVP): single Cloud Run service, manual deploys
- Phase 2: custom domain, shared team projects, export formats

## 11. Development Guide

```bash
# Agent
cd agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=<proj>
export PARALLEL_API_KEY=<key>
uvicorn main:app --reload --port 8080

# Web
cd web && npm install
echo 'VITE_API_URL=http://localhost:8080' > .env.local
npm run dev
```

Scripts: `npm run build` (web), `gcloud run deploy verisim-api --source .` (agent).

## 12. Security

- API keys only in Secret Manager / env — never in repo
- Rate limiting per IP on research endpoints (protects Parallel quota)
- Input length caps (question ≤ 500 chars) to bound cost/abuse
- CORS restricted to Netlify domain
- Firestore security: server-side access only (no client SDK writes)
- No PII stored; dossiers are user-scoped by anonymous session token

## 13. Roadmap

- **v1.0 (MVP):** projects, research→dossier, citations UI, thread follow-ups, export MD
- **v1.1:** fact-conflict flagging (sources disagree), dossier templates (location, procedure, era), shareable read-only links
- **v2.0:** multi-file script upload → auto-suggest research questions per scene; team workspaces

## 14. Hackathon Compliance Map

| Rule | How Verisim satisfies |
|---|---|
| Powered by Gemini + Google Cloud Agent Builder | ADK agent on Vertex AI (Gemini); `google-adk` imported & called in `agent/agent.py` |
| Partner product at runtime (in code) | `parallel-web` SDK Search + Extract called in `agent/tools.py` |
| Media & entertainment workflow | Screenwriter research workflow |
| Public repo + OSI license | MIT license file at repo root |
| Hosted URL | Netlify (web) + Cloud Run (API) public endpoints |
| Only Google/partner AI | No other AI APIs anywhere |

## 15. Submission Blurb (EN)

### Problem
Screenwriters lose hours verifying real-world facts, and AI answers can't be trusted without sources.

### Solution
- Ask any research question about your script's world
- Gemini agent searches the live web via Parallel and synthesizes a cited dossier
- Save dossiers per project, drill deeper with follow-up threads, export to Markdown

### Technical Architecture
- React/Vite frontend (Netlify) + Python FastAPI agent on Google Cloud Run
- Google ADK agent powered by Gemini on Vertex AI Agent Builder
- Parallel Search + Extract APIs as native agent tools
- Firestore persistence

### What Makes It Different
- Citations-first UX: every claim links to a live source
- Built for a real craft workflow, not generic "chat with search"
- Dossiers accumulate into a project's private research bible
- Honest uncertainty: flags conflicting sources rather than blending them
- Sub-minute research turnaround vs hours of manual verification

### Built With
React, Vite, Tailwind, Python, FastAPI, google-adk, Gemini (Vertex AI), parallel-web SDK, Firestore, Cloud Run, Netlify

## 16. Ringkasan (ID)

**Masalah:** Skenarista membuang waktu berjam-jam memverifikasi fakta dunia nyata; jawaban AI tanpa sumber tidak bisa dipercaya.

**Solusi:** Verisim mengubah pertanyaan riset penulis menjadi dossier terstruktur dengan sitasi bernomor dalam hitungan detik — disimpan per proyek skenario, bisa ditindaklanjuti lewat thread, dan diekspor ke Markdown.

**Teknologi:** React/Vite + Tailwind (Netlify), FastAPI di Cloud Run, agen Google ADK berbasis Gemini (Vertex AI), Parallel Search & Extract API sebagai tools agen, Firestore untuk penyimpanan.

## 17. Judge Quickstart (repo requirement)

The repo must contain all instructions needed to run (hackathon rule). Judges need two free credentials we cannot ship: a Google Cloud project (Vertex AI + Firestore) and a Parallel API key.

```
# 1. Prerequisites (free)
#    - Google Cloud project with Vertex AI + Firestore enabled (free trial works)
#    - Parallel API key: sign up at parallel.ai playground
# 2. Run
git clone https://github.com/<owner>/verisim && cd verisim
cp .env.example .env            # fill GOOGLE_CLOUD_PROJECT, PARALLEL_API_KEY
gcloud auth application-default login
docker compose up               # agent :8080, web :5173
# 3. Open http://localhost:5173 — create a project, ask a research question
```

- `.env.example` documents every required variable
- `docker-compose.yml` starts agent API + web UI in one command
- No secrets committed; keys via env only
- Hosted URL remains the primary judging path; repo proves runtime use of google-adk + parallel-web
