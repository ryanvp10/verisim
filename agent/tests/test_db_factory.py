"""Tests for the get_db() factory and the FirestoreDb backend.

All tests are offline: the Firestore SDK module is stubbed via the db
module namespace, or a MagicMock client is injected directly.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import db as db_module
from db import FakeDb, FirestoreDb, get_db
from schemas import DossierOut, ProjectCreate, Source, ThreadMsgOut

T0 = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def make_project(**overrides) -> ProjectCreate:
    payload = {'title': 'Test Film', 'logline': 'A story', 'genre': 'drama'}
    payload.update(overrides)
    return ProjectCreate(**payload)


def make_msg(role: str, text: str) -> ThreadMsgOut:
    return ThreadMsgOut(role=role, text=text, created_at=T0)


def make_dossier(dossier_id: str = 'd-1') -> DossierOut:
    return DossierOut(
        dossier_id=dossier_id,
        question='What is this about?',
        answer='An answer.',
        sources=[
            Source(n=1, title='Example', url='https://example.com', excerpt='An excerpt.')
        ],
        created_at=T0,
    )


# ------------------------------------------------------------------ get_db()


def test_get_db_defaults_to_fake_when_env_unset(monkeypatch):
    monkeypatch.delenv('VERISIM_DB', raising=False)
    assert isinstance(get_db(), FakeDb)


def test_get_db_fake_value_returns_fake(monkeypatch):
    monkeypatch.setenv('VERISIM_DB', 'fake')
    assert isinstance(get_db(), FakeDb)


def test_get_db_firestore_returns_firestore_db(monkeypatch):
    monkeypatch.setenv('VERISIM_DB', 'firestore')
    # Stub the SDK module in the db module namespace so no real client,
    # credentials or network are involved.
    monkeypatch.setattr(db_module, 'firestore', SimpleNamespace(Client=lambda: object()))
    instance = get_db()
    assert isinstance(instance, FirestoreDb)
    # First use resolves the lazily-created client through the stub.
    assert instance.client is not None


# --------------------------------------------------------------- FirestoreDb


def test_create_and_save_dossier_match_firestore_layout():
    client = MagicMock()
    db = FirestoreDb(client=client)

    project = db.create_project(make_project())

    project_doc = client.collection.return_value.document.return_value
    snapshot = project_doc.get.return_value
    snapshot.exists = True
    snapshot.get.return_value = 0  # dossier_count before increment

    db.save_dossier(project.id, make_dossier('d-1'))

    # project doc: projects/{projectId}.set(...)
    projects_col = client.collection.return_value
    client.collection.assert_any_call('projects')
    projects_col.document.assert_any_call(project.id)

    project_doc.set.assert_called_once()  # create_project; the count uses update()
    project_payload = project_doc.set.call_args[0][0]
    assert 'dossier_count' in project_payload
    assert 'id' not in project_payload  # id lives in the document id only
    assert isinstance(project_payload['created_at'], str)  # ISO-serialized

    # dossier doc: projects/{pid}/dossiers/{did}.set(...)
    project_doc.collection.assert_called_with('dossiers')
    dossiers_col = project_doc.collection.return_value
    dossiers_col.document.assert_called_with('d-1')

    dossier_payload = dossiers_col.document.return_value.set.call_args[0][0]
    assert 'dossier_id' not in dossier_payload  # id lives in the document id only
    url = dossier_payload['sources'][0]['url']
    assert url == 'https://example.com/'  # pydantic normalizes; still a plain str
    assert isinstance(url, str)  # HttpUrl serialized to plain str on write
    assert isinstance(dossier_payload['created_at'], str)

    # dossier_count incremented via read-modify-write of the project doc
    assert snapshot.get.call_args[0][0] == 'dossier_count'
    project_doc.update.assert_called_once_with({'dossier_count': 1})


def test_save_dossier_unknown_project_raises_key_error():
    client = MagicMock()
    db = FirestoreDb(client=client)
    snapshot = client.collection.return_value.document.return_value.get.return_value
    snapshot.exists = False

    with pytest.raises(KeyError):
        db.save_dossier('ghost-project', make_dossier('d-x'))

    dossier_doc = (
        client.collection.return_value.document.return_value.collection.return_value.document.return_value
    )
    dossier_doc.set.assert_not_called()  # nothing written


def test_append_thread_unknown_dossier_raises_key_error():
    client = MagicMock()
    client.collection_group.return_value.stream.return_value = iter([])
    db = FirestoreDb(client=client)

    with pytest.raises(KeyError):
        db.append_thread('ghost-dossier', make_msg('user', 'hello'))
