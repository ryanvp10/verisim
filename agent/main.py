import contextlib
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request

import tools
from agent import run_research
from db import get_db as _db_factory
from schemas import DossierCreate, DossierOut, ProjectCreate, ProjectOut, Source


# Research endpoint rate limiting: sliding window per client ip, in-process.
RESEARCH_RATE_LIMIT = 30
RESEARCH_RATE_WINDOW_SECONDS = 3600
# client ip -> list of accepted-call timestamps via time.monotonic()
_rate_bucket: dict[str, list[float]] = {}


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Attach the datastore on startup unless it was pre-injected (tests)."""
    if not hasattr(app.state, "db"):
        app.state.db = _db_factory()
    yield


app = FastAPI(title="verisim-api", lifespan=lifespan)


def get_db(request: Request):
    """Dependency giving routes access to the app-level datastore."""
    return request.app.state.db


def _check_rate_limit(request: Request) -> None:
    """Prune stale timestamps then enforce the per-ip research rate limit.

    Raises:
        HTTPException: 429 when the client already made RESEARCH_RATE_LIMIT
            calls within RESEARCH_RATE_WINDOW_SECONDS.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    stamps = [
        t
        for t in _rate_bucket.setdefault(client_ip, [])
        if now - t < RESEARCH_RATE_WINDOW_SECONDS
    ]
    _rate_bucket[client_ip] = stamps
    if len(stamps) >= RESEARCH_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    stamps.append(now)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db=Depends(get_db)):
    return db.create_project(payload)


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db=Depends(get_db)):
    return db.list_projects()


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db=Depends(get_db)):
    project = db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@app.post(
    "/api/projects/{project_id}/research",
    response_model=DossierOut,
    status_code=201,
)
def create_research(
    project_id: str,
    payload: DossierCreate,
    request: Request,
    db=Depends(get_db),
):
    """Run research for one question and persist the resulting dossier."""
    _check_rate_limit(request)

    if db.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="project not found")

    research_fn = getattr(app.state, "research_fn", None) or run_research
    try:
        result = research_fn(payload.question)
    except tools.ToolError as exc:
        raise HTTPException(status_code=502, detail="research failed") from exc

    sources = [
        Source(
            n=n,
            title=str(src.get("title") or ""),
            url=src["url"],
            excerpt=(src.get("excerpt") or "")[:500],
        )
        for n, src in enumerate(result.get("sources") or [], start=1)
    ]
    dossier = DossierOut(
        dossier_id=uuid.uuid4().hex,
        question=payload.question,
        answer=result["answer"],
        findings=result.get("findings") or [],
        notes=result.get("notes") or [],
        sources=sources,
        status="done",
        created_at=datetime.now(timezone.utc),
    )
    db.save_dossier(project_id, dossier)
    return dossier
