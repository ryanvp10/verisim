"""Tests for the in-memory FakeDb layer."""

from datetime import datetime, timezone

import pytest

from db import FakeDb
from schemas import DossierOut, ProjectCreate, ThreadMsgOut

T0 = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def make_project(**overrides) -> ProjectCreate:
    payload = {'title': 'Test Film', 'logline': 'A story', 'genre': 'drama'}
    payload.update(overrides)
    return ProjectCreate(**payload)


def make_dossier(dossier_id: str, created_at: datetime) -> DossierOut:
    return DossierOut(
        dossier_id=dossier_id,
        question='What is this about?',
        answer='An answer.',
        created_at=created_at,
    )


def make_msg(role: str, text: str) -> ThreadMsgOut:
    return ThreadMsgOut(role=role, text=text, created_at=T0)


def test_create_list_get_roundtrip_preserves_fields():
    db = FakeDb()
    created = db.create_project(make_project(title='Roundtrip', genre='sci-fi'))

    assert db.list_projects() == [created]

    fetched = db.get_project(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.title == 'Roundtrip'
    assert fetched.logline == 'A story'
    assert fetched.genre == 'sci-fi'
    assert fetched.dossier_count == 0
    assert fetched.created_at == created.created_at


def test_save_dossier_increments_dossier_count():
    db = FakeDb()
    project = db.create_project(make_project())

    db.save_dossier(project.id, make_dossier('d1', T0))
    assert db.get_project(project.id).dossier_count == 1

    db.save_dossier(project.id, make_dossier('d2', T0))
    assert db.get_project(project.id).dossier_count == 2


def test_get_dossier_returns_saved_dossier():
    db = FakeDb()
    project = db.create_project(make_project())
    saved = make_dossier('d-42', T0)

    db.save_dossier(project.id, saved)
    assert db.get_dossier('d-42') == saved


def test_list_dossiers_newest_first():
    db = FakeDb()
    project = db.create_project(make_project())
    older = make_dossier('d-old', datetime(2026, 8, 21, 9, 0, 0, tzinfo=timezone.utc))
    newest = make_dossier('d-new', datetime(2026, 8, 22, 15, 30, 0, tzinfo=timezone.utc))
    middle = make_dossier('d-mid', T0)

    db.save_dossier(project.id, older)
    db.save_dossier(project.id, newest)
    db.save_dossier(project.id, middle)

    listed = db.list_dossiers(project.id)
    assert [d.dossier_id for d in listed] == ['d-new', 'd-mid', 'd-old']


def test_append_thread_then_get_thread_in_order():
    db = FakeDb()
    project = db.create_project(make_project())
    db.save_dossier(project.id, make_dossier('d-thread', T0))

    first = make_msg('user', 'hello')
    second = make_msg('assistant', 'hi there')
    db.append_thread('d-thread', first)
    db.append_thread('d-thread', second)

    thread = db.get_thread('d-thread')
    assert thread == [first, second]


def test_get_project_missing_returns_none():
    db = FakeDb()
    assert db.get_project('nope') is None


def test_save_dossier_unknown_project_raises_key_error():
    db = FakeDb()
    with pytest.raises(KeyError):
        db.save_dossier('ghost-project', make_dossier('d-x', T0))
