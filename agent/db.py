"""Datastore backends for the verisim agent.

FakeDb is pure dict-backed in-memory storage, no external services: all
data lives for the lifetime of the instance. FirestoreDb mirrors the same
8-method contract on top of Google Cloud Firestore. get_db() picks the
backend from the VERISIM_DB environment variable ('firestore' selects
FirestoreDb, anything else falls back to FakeDb).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

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


# Module-level handle for the google.cloud.firestore module. It stays None
# until first use so that importing this module never imports the SDK nor
# requires credentials; tests may monkeypatch this name with a stub.
firestore: Any | None = None

_PROJECTS = 'projects'
_DOSSIERS = 'dossiers'
_THREAD = 'thread'


def _load_firestore_module() -> Any:
    """Return the (cached) google.cloud.firestore module, importing lazily.

    Reads the module-global ``firestore`` first so a monkeypatched stub in
    the db module namespace takes precedence over the real SDK import.
    """
    global firestore
    if firestore is None:
        from google.cloud import firestore as firestore_module

        firestore = firestore_module
    return firestore


class FirestoreDb:
    """Firestore-backed implementation of the same contract as FakeDb.

    Collection layout:

      projects/{projectId}
          title, logline, genre, created_at, dossier_count
      projects/{projectId}/dossiers/{dossierId}
          question, answer, findings, notes, sources, status, created_at
      projects/{projectId}/dossiers/{dossierId}/thread/{autoId}
          role, text, sources_used, created_at

    Document ids are not stored as fields: ProjectOut.id / DossierOut.dossier_id
    are injected from the Firestore document id on read.

    The optional ``client`` keyword accepts a pre-built client (handy for
    tests); otherwise one is created lazily on FIRST USE via
    ``firestore.Client()``, so constructing this class is always cheap and
    side-effect free.
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Lazily create the Firestore client on first use."""
        if self._client is None:
            self._client = _load_firestore_module().Client()
        return self._client

    # ------------------------------------------------------------- doc refs

    def _project_doc(self, project_id: str) -> Any:
        return self.client.collection(_PROJECTS).document(project_id)

    def _dossier_doc(self, project_id: str, dossier_id: str) -> Any:
        return self._project_doc(project_id).collection(_DOSSIERS).document(dossier_id)

    def _find_dossier(self, dossier_id: str) -> Any | None:
        """Locate a dossier doc by id across all projects (collection group)."""
        for snap in self.client.collection_group(_DOSSIERS).stream():
            if snap.id == dossier_id:
                return snap
        return None

    # ------------------------------------------------------------- projects

    def create_project(self, p: ProjectCreate) -> ProjectOut:
        project = ProjectOut(
            id=uuid.uuid4().hex,
            title=p.title,
            logline=p.logline,
            genre=p.genre,
            dossier_count=0,
            created_at=datetime.now(timezone.utc),
        )
        self._project_doc(project.id).set(
            project.model_dump(mode='json', exclude={'id'})
        )
        return project

    def list_projects(self) -> list[ProjectOut]:
        projects: list[ProjectOut] = []
        for snap in self.client.collection(_PROJECTS).stream():
            data = snap.to_dict()
            data['id'] = snap.id
            projects.append(ProjectOut.model_validate(data))
        return projects

    def get_project(self, project_id: str) -> ProjectOut | None:
        snap = self._project_doc(project_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict()
        data['id'] = snap.id
        return ProjectOut.model_validate(data)

    # ------------------------------------------------------------- dossiers

    def save_dossier(self, project_id: str, d: DossierOut) -> None:
        project_ref = self._project_doc(project_id)
        snapshot = project_ref.get()
        if not snapshot.exists:
            raise KeyError(f'unknown project: {project_id}')
        self._dossier_doc(project_id, d.dossier_id).set(
            d.model_dump(mode='json', exclude={'dossier_id'})
        )
        # Read-modify-write the counter on the project doc.
        count = snapshot.get('dossier_count') + 1
        project_ref.update({'dossier_count': count})

    def get_dossier(self, dossier_id: str) -> DossierOut | None:
        snap = self._find_dossier(dossier_id)
        if snap is None:
            return None
        data = snap.to_dict()
        data['dossier_id'] = snap.id
        return DossierOut.model_validate(data)

    def list_dossiers(self, project_id: str) -> list[DossierOut]:
        fs = _load_firestore_module()
        dossiers: list[DossierOut] = []
        for snap in (
            self._project_doc(project_id)
            .collection(_DOSSIERS)
            .order_by('created_at', direction=fs.Query.DESCENDING)
            .stream()
        ):
            data = snap.to_dict()
            data['dossier_id'] = snap.id
            dossiers.append(DossierOut.model_validate(data))
        return dossiers

    # -------------------------------------------------------------- threads

    def append_thread(self, dossier_id: str, msg: ThreadMsgOut) -> None:
        snap = self._find_dossier(dossier_id)
        if snap is None:
            raise KeyError(f'unknown dossier: {dossier_id}')
        snap.reference.collection(_THREAD).document().set(msg.model_dump(mode='json'))

    def get_thread(self, dossier_id: str) -> list[ThreadMsgOut]:
        snap = self._find_dossier(dossier_id)
        if snap is None:
            return []
        messages: list[ThreadMsgOut] = []
        for doc in snap.reference.collection(_THREAD).order_by('created_at').stream():
            messages.append(ThreadMsgOut.model_validate(doc.to_dict()))
        return messages


def get_db() -> FakeDb | FirestoreDb:
    """Pick the backend from VERISIM_DB: 'firestore' -> FirestoreDb, else FakeDb."""
    if os.environ.get('VERISIM_DB') == 'firestore':
        return FirestoreDb()
    return FakeDb()
