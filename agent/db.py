"""In-memory fake database for the verisim agent.

Pure dict-backed storage, no external services. All data lives for the
lifetime of the FakeDb instance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from schemas import DossierOut, ProjectCreate, ProjectOut, ThreadMsgOut


class FakeDb:
    """Minimal in-memory datastore keyed like a real relational DB would be."""

    def __init__(self) -> None:
        self._projects: dict[str, ProjectOut] = {}
        # dossier_id -> DossierOut, across all projects
        self._dossiers: dict[str, DossierOut] = {}
        # project_id -> [dossier_id, ...] in creation order
        self._dossiers_by_project: dict[str, list[str]] = {}
        # dossier_id -> [ThreadMsgOut, ...] in append order
        self._threads: dict[str, list[ThreadMsgOut]] = {}

    # ------------------------------------------------------------------ projects

    def create_project(self, p: ProjectCreate) -> ProjectOut:
        project = ProjectOut(
            id=uuid.uuid4().hex,
            title=p.title,
            logline=p.logline,
            genre=p.genre,
            dossier_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self._projects[project.id] = project
        self._dossiers_by_project[project.id] = []
        return project

    def list_projects(self) -> list[ProjectOut]:
        return list(self._projects.values())

    def get_project(self, project_id: str) -> ProjectOut | None:
        return self._projects.get(project_id)

    # ------------------------------------------------------------------ dossiers

    def save_dossier(self, project_id: str, d: DossierOut) -> None:
        project = self._projects.get(project_id)
        if project is None:
            raise KeyError(f'unknown project: {project_id}')
        self._dossiers[d.dossier_id] = d
        self._dossiers_by_project[project_id].append(d.dossier_id)
        project.dossier_count += 1

    def get_dossier(self, dossier_id: str) -> DossierOut | None:
        return self._dossiers.get(dossier_id)

    def list_dossiers(self, project_id: str) -> list[DossierOut]:
        ids = self._dossiers_by_project.get(project_id, [])
        dossiers = [self._dossiers[i] for i in ids]
        dossiers.sort(key=lambda d: d.created_at, reverse=True)
        return dossiers

    # ------------------------------------------------------------------ threads

    def append_thread(self, dossier_id: str, msg: ThreadMsgOut) -> None:
        if dossier_id not in self._threads and dossier_id not in self._dossiers:
            raise KeyError(f'unknown dossier: {dossier_id}')
        self._threads.setdefault(dossier_id, []).append(msg)

    def get_thread(self, dossier_id: str) -> list[ThreadMsgOut]:
        return list(self._threads.get(dossier_id, []))
