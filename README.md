# Verisim

> Research receipts for fiction writers.

Verisim is an AI research desk for screenwriters. Ask a real-world question about your script's world — get a cited research dossier in seconds, not days.

- 🎬 Built for filmmakers, screenwriters, and studio crews
- 🔍 Live web search via [Parallel](https://parallel.ai) Search & Extract APIs
- ✨ Powered by Gemini on Google Cloud (ADK agent)
- 📚 Every claim linked to a numbered source

## What is Verisim

Verisim answers real-world questions about your script's world with receipts. You create a project (title, logline, genre), ask a question like *"What does a 1970s precinct paperwork backlog actually look like?"*, and the backend runs an ADK agent — Gemini with two Parallel Search/Extract tools — that searches the live web and returns a structured dossier: an answer with bracketed numeric citations `[1]`, key findings, detailed notes, and a numbered source list with excerpts. Dossiers are saved per project, support follow-up Q&A threads, and export as markdown. Persistence is pluggable: the default in-memory store means zero infrastructure to run it.

Built for the [Agentic Cinema hackathon](https://agentic-cinema.devpost.com) (Google Cloud × Devpost). Product spec: [`SPEC.md`](SPEC.md).

## Quickstart for judges

Two free API keys are all you need — **no `gcloud`, no GCP project, no Firestore** (`VERISIM_DB=fake` runs an in-memory database by default):

- `PARALLEL_API_KEY` — sign up at [parallel.ai](https://parallel.ai)
- `GOOGLE_API_KEY` — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Option A — Docker

```bash
cp .env.example .env    # fill in PARALLEL_API_KEY and GOOGLE_API_KEY
docker compose up --build
# open http://localhost:5173
```

Compose loads `.env` into the agent container via `env_file`; the web dev server inside Docker proxies `/api` requests to the backend, so no extra config is needed.

> **Note:** `web/Dockerfile` is still a scaffold placeholder (no build instructions yet), so today `docker compose up --build` reliably starts the **agent** service only. Until the web image lands, run the agent container as above plus the two frontend commands from Option B.

### Option B — Manual

Backend (Python 3.11+):

```bash
cd agent
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GOOGLE_API_KEY=<your key>      # Gemini API key (see auth note below)
export PARALLEL_API_KEY=<your key>    # required for live research
.venv/bin/uvicorn main:app --port 8080
```

Frontend (Node 18+, second terminal):

```bash
cd web
npm install
npm run dev    # http://localhost:5173 — Vite proxies /api to localhost:8080
```

**How Gemini auth actually works here:** the agent uses google-adk's `LlmAgent`/`InMemoryRunner`, which talk to Gemini through the `google-genai` client in its default **Gemini Developer API** mode (the code never sets `GOOGLE_GENAI_USE_VERTEXAI`). On this path the credential checked is `GOOGLE_API_KEY` from Google AI Studio — plain HTTPS, no service accounts. You do **not** need `gcloud auth application-default login`; ADC is only required if you opt into Firestore (`VERISIM_DB=firestore`) or flip the stack to Vertex AI. Note that `.env` is *not* auto-loaded by uvicorn — either export the two keys or `set -a; source ../.env; set +a`.

### Vertex AI mode (production)

The same agent code can also run on **Vertex AI** for GCP production deployments: set `GOOGLE_GENAI_USE_VERTEXAI=true` along with `GOOGLE_CLOUD_PROJECT`, and the google-genai client underneath ADK switches from the Developer API key path to Vertex AI automatically. Authentication then uses Application Default Credentials instead of an API key — run `gcloud auth application-default login` locally, or rely on the Cloud Run service account's attached identity in prod. No `GOOGLE_API_KEY` secret is needed in this mode.

Without `PARALLEL_API_KEY`, `/health` and project CRUD still respond, but research requests fail with `502 research failed` (the Parallel tools refuse to start).

## Environment variables

| Variable | Required | What it does |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Required (live research) | Gemini API key from [AI Studio](https://aistudio.google.com/apikey); authenticates the google-genai client behind the ADK agent. |
| `PARALLEL_API_KEY` | Required (live research) | Key for the Parallel Search & Extract APIs ([parallel.ai](https://parallel.ai)); missing/empty key makes every research call return 502. |
| `GEMINI_MODEL` | Optional | Model override for the agent; defaults to `gemini-2.5-flash`. |
| `VERISIM_DB` | Optional | `fake` (default) = in-memory dict-backed store, data lives until restart, **no external services**. `firestore` = Google Cloud Firestore (needs ADC credentials and a project). |
| `GOOGLE_CLOUD_PROJECT` | Optional | Never read by app code in the default fake-DB setup. Only becomes relevant with `VERISIM_DB=firestore` or a Vertex AI switch. Safe to leave empty for judging. |
| `GOOGLE_GENAI_USE_VERTEXAI` | Optional | `true` enables Vertex AI mode instead of the Developer API key path (requires `GOOGLE_CLOUD_PROJECT` + ADC/service account; no `GOOGLE_API_KEY` needed). |
| `VITE_API_URL` | Optional (build-time) | Backend URL baked into the frontend bundle by Vite. Leave unset for local dev — the Vite dev proxy already forwards `/api` to `localhost:8080`. Set it in your host's UI (e.g. Netlify) for production builds. |

## Architecture

- **Frontend** — React 19 + Vite + Tailwind SPA (project pages, ask box, dossier view with clickable citations, follow-up thread panel, markdown export)
- **Backend** — FastAPI (`agent/main.py`): projects, dossiers, threads, export, per-IP rate limiting
- **Agent** — Google ADK `LlmAgent` (Gemini) with two tools backed by the Parallel Search API (`parallel_search`, `parallel_extract`), emitting strict JSON dossiers with numbered citations
- **Storage** — pluggable datastore: in-memory `FakeDb` by default, real Firestore via `VERISIM_DB=firestore` (same interface, `agent/db.py`)
- **Dossiers** — every claim carries a bracketed `[n]` citation linked to a numbered, excerpted source; exportable as markdown

## Running tests

```bash
cd agent && .venv/bin/pytest -q        # 62 tests, fully offline (runner stubbed)
cd web && npm run build                # production build check
```

## Deploying

**Backend → Cloud Run** (sketch — create the secrets first with `gcloud secrets create`):

```bash
gcloud run deploy verisim-api \
  --source agent \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --set-env-vars VERISIM_DB=fake,GOOGLE_GENAI_USE_VERTEXAI=true \
  --set-secrets PARALLEL_API_KEY=parallel-key:latest
```

Switch `VERISIM_DB=firestore` (plus a service account with Firestore access) when you want persistence across deploys.

**Frontend → Netlify or Cloudflare Pages**: import the repo and set **base/root directory** `web`, **build command** `npm run build`, **publish/output directory** `web/dist`; add `VITE_API_URL=https://<your-cloud-run-url>` in the host UI's environment variables before building. Heads-up: the backend currently ships no CORS middleware, so cross-origin calls from the frontend domain require enabling CORS server-side (or serving both tiers from one domain).

---

🚧 Hackathon build — expect sharp edges. See [`SPEC.md`](SPEC.md) for the product spec.
