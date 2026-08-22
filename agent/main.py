import contextlib

from fastapi import Depends, FastAPI, HTTPException, Request

from db import get_db as _db_factory
from schemas import ProjectCreate, ProjectOut


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
