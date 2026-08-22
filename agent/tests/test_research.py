"""Tests for POST /api/projects/{project_id}/research (Task B4).

Fully offline: agent.run_research is replaced by a canned fake injected on
app.state.research_fn, and the rate-limit bucket is cleared between tests.
"""

import pytest
from fastapi.testclient import TestClient

import main
import tools
from db import FakeDb


def _canned_research(question: str) -> dict:
    """Offline stand-in for agent.run_research output."""
    return {
        "answer": "Research done [1] [2]",
        "findings": ["finding one"],
        "notes": ["note one"],
        "sources": [
            {
                "n": 7,  # must be ignored: endpoint renumbers from 1
                "title": "A",
                "url": "https://a.example.com",
                "excerpt": "x" * 600,  # must be truncated to 500 chars
            },
            {  # no title key -> endpoint must default to ''
                "url": "https://b.example.com",
                "excerpt": "short",
            },
        ],
    }


@pytest.fixture()
def client():
    """Fresh FakeDb + canned research_fn; rate bucket cleared between tests."""
    main.app.state.db = FakeDb()
    main.app.state.research_fn = _canned_research
    main._rate_bucket.clear()
    with TestClient(main.app) as c:
        yield c


def _new_project(client) -> str:
    return client.post("/api/projects", json={"title": "Test Film"}).json()["id"]


def test_research_happy_path_returns_201_and_persists(client):
    pid = _new_project(client)

    resp = client.post(f"/api/projects/{pid}/research", json={"question": "Who?"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["dossier_id"]
    assert body["question"] == "Who?"
    assert body["answer"] == "Research done [1] [2]"
    assert body["findings"] == ["finding one"]
    assert body["notes"] == ["note one"]
    assert body["status"] == "done"
    # Sources renumbered sequentially from 1; incoming n=7 is ignored.
    assert [s["n"] for s in body["sources"]] == [1, 2]
    assert len(body["sources"][0]["excerpt"]) == 500
    assert body["sources"][1]["title"] == ""

    db = main.app.state.db
    assert len(db.list_dossiers(pid)) == 1
    assert db.get_project(pid).dossier_count == 1


def test_research_unknown_project_returns_404(client):
    resp = client.post(
        "/api/projects/no-such-id/research", json={"question": "Who?"}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "project not found"


def test_research_overlong_question_returns_422(client):
    pid = _new_project(client)

    resp = client.post(
        f"/api/projects/{pid}/research", json={"question": "x" * 501}
    )

    assert resp.status_code == 422


def test_research_third_call_within_limit_returns_429(client, monkeypatch):
    pid = _new_project(client)
    monkeypatch.setattr(main, "RESEARCH_RATE_LIMIT", 2)

    r1 = client.post(f"/api/projects/{pid}/research", json={"question": "q1?"})
    r2 = client.post(f"/api/projects/{pid}/research", json={"question": "q2?"})
    r3 = client.post(f"/api/projects/{pid}/research", json={"question": "q3?"})

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r3.status_code == 429
    assert r3.json()["detail"] == "rate limit exceeded"


def test_research_fn_raising_tool_error_returns_502(client):
    def boom(question: str):
        raise tools.ToolError("offline boom")

    main.app.state.research_fn = boom
    pid = _new_project(client)

    resp = client.post(f"/api/projects/{pid}/research", json={"question": "Who?"})

    assert resp.status_code == 502
    assert resp.json()["detail"] == "research failed"
