import contextlib
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
import tools
from agent import run_research
from db import get_db as _db_factory
from schemas import (
    DossierCreate,
    DossierOut,
    ProjectCreate,
    ProjectOut,
    Source,
    ThreadMsgIn,
    ThreadMsgOut,
)


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


@app.get("/api/projects/{project_id}/dossiers", response_model=list[DossierOut])
def list_project_dossiers(project_id: str, db=Depends(get_db)):
    """List all dossiers for a project, newest first."""
    project = db.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return db.list_dossiers(project_id)


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


@app.post(
    "/api/dossiers/{dossier_id}/thread",
    response_model=list[ThreadMsgOut],
)
def post_thread_message(
    dossier_id: str,
    payload: ThreadMsgIn,
    request: Request,
    db=Depends(get_db),
):
    """Append a user follow-up and the agent reply to a dossier thread."""
    _check_rate_limit(request)

    dossier = db.get_dossier(dossier_id)
    if dossier is None:
        raise HTTPException(status_code=404, detail="dossier not found")

    now = datetime.now(timezone.utc)
    db.append_thread(
        dossier_id,
        ThreadMsgOut(role="user", text=payload.message, sources_used=[], created_at=now),
    )

    # Thread context: original question + answer, then each prior message.
    prior = db.get_thread(dossier_id)
    context_lines = [dossier.question, dossier.answer]
    context_lines += [f"{msg.role}: {msg.text}" for msg in prior]
    context = "\n\n".join(context_lines)

    research_fn = getattr(app.state, "research_fn", None) or run_research
    try:
        result = research_fn(context)
    except tools.ToolError as exc:
        raise HTTPException(status_code=502, detail="research failed") from exc

    sources_used = list(range(1, len(result.get("sources") or []) + 1))
    db.append_thread(
        dossier_id,
        ThreadMsgOut(
            role="agent",
            text=result["answer"],
            sources_used=sources_used,
            created_at=datetime.now(timezone.utc),
        ),
    )
    return db.get_thread(dossier_id)


@app.get("/api/dossiers/{dossier_id}/thread", response_model=list[ThreadMsgOut])
def get_dossier_thread(dossier_id: str, db=Depends(get_db)):
    """Return the full follow-up thread for one dossier."""
    if db.get_dossier(dossier_id) is None:
        raise HTTPException(status_code=404, detail="dossier not found")
    return db.get_thread(dossier_id)


@app.get("/api/dossiers/{dossier_id}/export")
def export_dossier(dossier_id: str, db=Depends(get_db)):
    """Render one dossier as a downloadable markdown document."""
    dossier = db.get_dossier(dossier_id)
    if dossier is None:
        raise HTTPException(status_code=404, detail="dossier not found")

    lines = [f"# {dossier.question}", "", "## Answer", "", dossier.answer, ""]
    for title, items in (("Key Findings", dossier.findings), ("Detailed Notes", dossier.notes)):
        lines.append(f"## {title}")
        lines.append("")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("No findings recorded")
        lines.append("")
    lines.append("## Sources")
    lines.append("")
    lines.extend(f"{s.n}. {s.title} - {s.url}" for s in dossier.sources)

    markdown = "\n".join(lines)
    filename = f"verisim-dossier-{dossier_id[:8]}.md"
    return Response(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
