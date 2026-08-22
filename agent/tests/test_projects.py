"""Tests for the /api/projects REST endpoints."""

import pytest
from fastapi.testclient import TestClient

import main
from db import FakeDb


@pytest.fixture()
def client():
    """Fresh FakeDb per test, pre-injected before the lifespan startup runs."""
    main.app.state.db = FakeDb()
    with TestClient(main.app) as c:
        yield c


def _project_payload(title: str = "Test Film") -> dict:
    return {"title": title, "logline": "A story", "genre": "drama"}


def test_create_project_returns_201_with_full_body(client):
    resp = client.post("/api/projects", json=_project_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["title"] == "Test Film"
    assert body["logline"] == "A story"
    assert body["genre"] == "drama"
    assert body["dossier_count"] == 0
    assert body["created_at"]


def test_list_projects_contains_created_project(client):
    created = client.post("/api/projects", json=_project_payload()).json()

    resp = client.get("/api/projects")

    assert resp.status_code == 200
    projects = resp.json()
    assert isinstance(projects, list)
    assert len(projects) == 1
    assert projects[0]["id"] == created["id"]


def test_get_project_by_id_returns_matching_title(client):
    created = client.post("/api/projects", json=_project_payload()).json()

    resp = client.get(f"/api/projects/{created['id']}")

    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Film"


def test_get_unknown_project_returns_404(client):
    resp = client.get("/api/projects/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "project not found"


def test_create_project_with_overlong_title_returns_422(client):
    resp = client.post("/api/projects", json=_project_payload("x" * 121))

    assert resp.status_code == 422
