# Verisim Implementation Plan

> **For Hermes:** Dispatch ONE task at a time to Alva (`hermes --profile worker`). PM runs QA + Security review after each task. User approves before next phase.

**Goal:** Build Verisim — a cited-research-dossier agent for screenwriters (Gemini/ADK + Parallel Search) — deployable and judge-runnable.

**Architecture:** React/Vite web (Netlify) → FastAPI agent on Cloud Run running a Google ADK agent (Gemini via Vertex AI) with Parallel Search/Extract as tools → Firestore persistence. See `/home/ubuntu/verisim/SPEC.md` (source of truth).

**Tech Stack:** React, Vite, Tailwind, Python 3.11+, FastAPI, google-adk, parallel-web, google-cloud-firestore, Docker.

**External dependencies (PM/user provides before Phase B integration):**
- `GOOGLE_CLOUD_PROJECT` with Vertex AI + Firestore enabled, ADC via `gcloud auth application-default login`
- `PARALLEL_API_KEY` from parallel.ai playground
- Empty GitHub repo `verisim`

**Rule for Alva:** If any SDK signature differs from these snippets (ADK / parallel-web evolve fast), FOLLOW THE OFFICIAL DOCS but keep our function contracts unchanged. Never invent API shapes — verify against docs.

---

## Phase A — Scaffold (no external keys needed)

### Task A1: Repo bootstrap
**Objective:** Initialize repo structure, license, git.
**Files:** Create `.gitignore`, `LICENSE` (MIT, holder "Verisim contributors"), `README.md` (stub: name + tagline only).
**Steps:** mkdir verisim subdirs (`web/`, `agent/`) → write files → `git init && git add -A && git commit -m "chore: bootstrap repo"`.
**Verify:** `git log --oneline` shows 1 commit; LICENSE present at root.

### Task A2: Python env + requirements
**Objective:** Agent package with pinned deps + pytest wired.
**Files:** Create `agent/requirements.txt`: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `google-adk`, `parallel-web`, `google-cloud-firestore`, `pytest`, `httpx`. Create `agent/tests/__init__.py`.
**Steps:** `cd agent && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install -e .` (add minimal `pyproject.toml`).
**Verify:** `.venv/bin/python -c "import fastapi, google.adk, parallel_web"` exits 0 (if `parallel_web` import name differs, check `pip show parallel-web`).

### Task A3: FastAPI skeleton + health check (TDD)
**Files:** Test `agent/tests/test_main.py`; impl `agent/main.py`.
**Step 1 failing test:**
```python
from fastapi.testclient import TestClient
from main import app

def test_health():
    c = TestClient(app)
    assert c.get("/health").json() == {"status": "ok"}
```
Run: `cd agent && .venv/bin/pytest tests/test_main.py -v` → FAIL.
**Step 2 impl:** `app = FastAPI(title="verisim-api")` + `@app.get("/health")`.
Run again → PASS. Commit `feat: fastapi skeleton`.

### Task A4: Pydantic schemas
**Files:** `agent/schemas.py`, test `agent/tests/test_schemas.py`.
Models per SPEC §7: `ProjectCreate{title:str(max 120), logline:str(max 500, default ""), genre:str(max 40, default "")}`, `ProjectOut{id,title,logline,genre,dossier_count:int,created_at}`, `Source{n:int,title,url:HttpUrl,excerpt:str(max 500)}`, `DossierCreate{question:str(max 500)}`, `DossierOut{dossier_id,question,answer,findings:list[str],notes:list[str],sources:list[Source],status,created_at}`, `ThreadMsgIn{message:str(max 500)}`, `ThreadMsgOut{role,text,sources_used:list[int],created_at}`.
Test: invalid (>max length) raises ValidationError. Commit.

### Task A5: DB layer with in-memory fake (TDD)
**Files:** `agent/db.py` + `agent/tests/test_db.py`.
Interface (both implementations expose): `create_project(p:ProjectCreate)->ProjectOut`, `list_projects()->list[ProjectOut]`, `get_project(id)->ProjectOut|None`, `save_dossier(project_id,d:DossierOut)->None`, `get_dossier(id)->DossierOut|None`, `list_dossiers(project_id)->list[DossierOut]`, `append_thread(dossier_id,msg:ThreadMsgOut)->None`, `get_thread(dossier_id)->list[ThreadMsgOut]`.
- `FakeDb(dict-backed)` first (TDD: create→list→dossier save→thread append).
- `FirestoreDb` same methods using `google.cloud.firestore.Client`, collection paths per SPEC §8. Selected via env `VERISIM_DB` = `fake`(default) | `firestore`.
Commit `feat: db layer + fake`.

### Task A6: Docker
**Files:** root `docker-compose.yml`, `agent/Dockerfile`, `web/Dockerfile` (placeholder until C1), root `.env.example`:
```
GOOGLE_CLOUD_PROJECT=
PARALLEL_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
VERISIM_DB=fake
VITE_API_URL=http://localhost:8080
```
Compose: services `agent` (build ./agent, ports 8080:8080, env_file .env, mounts ~/.config/gcloud:ro when present) and `web` (ports 5173:5173).
**Verify:** `docker compose config` valid YAML. Commit.

## Phase B — Agent core

### Task B1: Parallel tools wrapper (TDD, mocked)
**Files:** `agent/tools.py`, `agent/tests/test_tools.py`.
Contracts:
```python
def parallel_search(query: str, max_results: int = 10) -> list[dict]:
    """Returns [{n,title,url,excerpt}] — numbered."""

def parallel_extract(url: str) -> str:
    """Returns readable text content of url."""
```
Tests mock the `parallel-web` client; assert numbering starts at 1, exceptions raise `ToolError(msg)` (custom). Real HTTP call lives behind `_get_client()` so tests never hit network. **Alva must verify exact SDK calls against docs.parallel.ai Search API quickstart.** Env-keyed, import-safe without key (lazy client). Commit.

### Task B2: ADK agent definition
**Files:** `agent/agent.py`.
```python
from google.adk.agents import LlmAgent
from tools import parallel_search, parallel_extract

SYSTEM = (
 "You are Verisim, a research assistant for screenwriters. "
 "For every user question: run parallel_search, optionally parallel_extract "
 "on the 2-3 most promising URLs, then synthesize. Output STRICT JSON: "
 '{"answer": str with [n] citations, "findings": [str], '
 '"notes": [str], "sources": [{n,title,url,excerpt}]}'
)

def build_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name="verisim",
        model=model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        instruction=SYSTEM,
        tools=[parallel_search, parallel_extract],
    )
```
Plus `run_research(question:str)->dict`: creates InMemoryRunner, runs session, parses JSON (strip code fences; on parse failure retry once with "return ONLY valid JSON"). Unit test with a stubbed runner asserting JSON parsing + fence stripping. **Verify ADK API names against current docs.** Commit.

### Task B3: Projects endpoints (TDD)
**Files:** modify `main.py`, tests `test_projects.py`.
`POST /api/projects` (201, ProjectOut), `GET /api/projects`, `GET /api/projects/{id}` (404 case). Uses db interface; tests inject FakeDb via app.state. Verify + commit.

### Task B4: Research endpoint (TDD, fake agent)
**Files:** modify `main.py`; `tests/test_research.py`.
`POST /api/projects/{id}/research` body `DossierCreate` → runs injected `app.state.research_fn(question)->dict` (defaults to `run_research`), maps result into `DossierOut` (status "done", uuid dossier_id), persists, returns 201. Test uses canned fake fn; assert sources re-numbered 1..n and persisted. Rate limit guard: simple in-memory counter, 30 req/hour/IP → 429. Commit.

### Task B5: Thread + export endpoints (TDD)
`POST /api/dossiers/{id}/thread` (ThreadMsgIn) → appends user msg, calls research_fn with thread context, appends agent msg, returns full thread. `GET /api/dossiers/{id}/export` → `text/markdown` attachment built from dossier (title=question, sections Answer/Findings/Notes/Sources). Tests for both incl. 404s. Commit.

## Phase C — Web

### Task C1: Vite scaffold
`npm create vite@latest web -- --template react` + Tailwind v4 (`@tailwindcss/vite`, `@import "tailwindcss"` in index.css). Dark theme tokens in `@theme`: bg `#0f1115`, panel `#171a21`, paper `#f7f4ec`, accent amber `#d97706`. Fonts: serif headings (Georgia/'Playfair Display'), sans body. Wire dev proxy `/api → http://localhost:8080`. Verify `npm run build` passes. Commit.

### Task C2: API client + ProjectsPage
`src/api.js` (fetch wrapper, base `import.meta.env.VITE_API_URL || ''`). Pages per SPEC §9: grid of project cards (title, logline, genre chip, dossier count), "+ New Project" modal → POST → navigate. Loading/error states. Mobile-first, no horizontal scroll, `break-words` everywhere. Commit.

### Task C3: ProjectPage + AskBox + dossiers list
Route `/project/:id`. AskBox (textarea ≤500 chars, char counter, "Research" button → spinner state ≥1 pending request). DossierCard list newest-first (question, date, n-sources badge). Commit.

### Task C4: DossierView + citations
Full dossier: sections Answer / Key Findings / Detailed Notes / Sources. Render `[n]` in answer/findings as clickable superscript chips → right-side drawer (mobile: bottom sheet) showing title, excerpt, external link. Numbered source rows. Commit.

### Task C5: ThreadPanel + Export
Chat-style thread under dossier view; send → optimistic user bubble → reply with its own `[n]` chips. "Export .md" button hits export endpoint (download attr). Commit.

## Phase D — Judge-ready + ship

### Task D1: Live integration pass (needs real keys)
With real `PARALLEL_API_KEY` + Vertex ADC: script `agent/scripts/smoke.py` — run_research("How does a Tokyo police interrogation work?") prints answer + sources. Fix JSON/tool issues. Then switch VERISIM_DB=firestore, verify roundtrip. Commit.

### Task D2: README Judge Quickstart
Per SPEC §17 exactly: prerequisites (free GCP trial + Parallel key), clone/cp/.env, `gcloud auth application-default login`, `docker compose up`, open localhost:5173. Add architecture diagram + compliance table (SPEC §14). Commit.

### Task D3: Deploy
Cloud Run: `gcloud run deploy verisim-api --source agent --region asia-southeast2 --set-env-vars ...` secrets via Secret Manager. Firestore native mode provisioned. Netlify: build web, set VITE_API_URL in Netlify UI. Smoke test hosted URL end-to-end (create → research → dossier renders). Record URLs. Commit.

### Task D4: Submission assets
Devpost text description (SPEC §15 EN blurb), repo About + topics, license visible. Demo video shot-list PM drafts separately. Final QA + Security review gate before submission.

---

## Verification gates (PM after each task)
1. Tests green: `cd agent && .venv/bin/pytest -q`
2. No secrets/keys in `git grep`
3. Contracts match SPEC §7 (field names/status codes)
4. Frontend: `npm run build` clean, mobile viewport 360px no horizontal scroll
5. Compliance: `grep -r "google" agent/pyproject.toml` shows google-adk; tools.py imports parallel_web
