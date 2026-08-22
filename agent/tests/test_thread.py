"""Tests for dossier thread follow-up + markdown export endpoints (Task B5).

Fully offline: agent.run_research is replaced by a canned fake injected on
app.state.research_fn, and the rate-limit bucket is cleared between tests.
The rate-limit token consumption of the thread endpoint itself is NOT tested.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import main
import tools
from db import FakeDb
from schemas import ThreadMsgOut


def _canned_followup(question: str) -> dict:
    """Offline stand-in for agent.run_research output."""
    return {
        "answer": "Follow-up answered",
        "sources": [
            {"title": "A", "url": "https://a.example.com", "excerpt": "short"},
            {"title": "B", "url": "https://b.example.com", "excerpt": "short"},
        ],
    }


@pytest.fixture()
def client():
    """Fresh FakeDb + canned research_fn; rate bucket cleared between tests."""
    main.app.state.db = FakeDb()
    main.app.state.research_fn = _canned_followup
    main._rate_bucket.clear()
    with TestClient(main.app) as c:
        yield c


@pytest.fixture()
def dossier_id(client) -> str:
    """Create a project and one real persisted dossier via the API."""
    pid = client.post("/api/projects", json={"title": "Thread Film"}).json()["id"]
    resp = client.post(f"/api/projects/{pid}/research", json={"question": "Who?"})
    assert resp.status_code == 201
    return resp.json()["dossier_id"]


def test_thread_happy_path_appends_user_and_agent_messages(client, dossier_id):
    resp = client.post(
        f"/api/dossiers/{dossier_id}/thread",
        json={"message": "What about the ending?"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["role"] == "user"
    assert body[0]["text"] == "What about the ending?"
    assert body[1]["role"] == "agent"
    assert body[1]["text"] == "Follow-up answered"
    assert body[1]["sources_used"] == [1, 2]
    db = main.app.state.db
    assert len(db.get_thread(dossier_id)) == 2


def test_thread_unknown_dossier_returns_404(client):
    resp = client.post(
        "/api/dossiers/no-such-id/thread", json={"message": "hello?"}
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "dossier not found"


def test_thread_overlong_message_returns_422(client, dossier_id):
    resp = client.post(
        f"/api/dossiers/{dossier_id}/thread", json={"message": "x" * 501}
    )

    assert resp.status_code == 422


def test_thread_research_fn_raising_tool_error_returns_502(client, dossier_id):
    def boom(question: str):
        raise tools.ToolError("offline boom")

    main.app.state.research_fn = boom

    resp = client.post(
        f"/api/dossiers/{dossier_id}/thread", json={"message": "go on"}
    )

    assert resp.status_code == 502
    assert resp.json()["detail"] == "research failed"


def test_export_returns_markdown_attachment(client, dossier_id):
    resp = client.get(f"/api/dossiers/{dossier_id}/export")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.text
    assert body.startswith("# Who?")
    assert "## Answer" in body
    assert "## Key Findings" in body
    assert "## Detailed Notes" in body
    assert "## Sources" in body
    assert "https://a.example.com" in body


def test_export_unknown_dossier_returns_404(client):
    resp = client.get("/api/dossiers/no-such-id/export")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "dossier not found"


def test_get_thread_returns_appended_messages_in_order(client, dossier_id):
    db = main.app.state.db
    now = datetime.now(timezone.utc)
    db.append_thread(
        dossier_id,
        ThreadMsgOut(role="user", text="What about the ending?", sources_used=[], created_at=now),
    )
    db.append_thread(
        dossier_id,
        ThreadMsgOut(role="agent", text="Follow-up answered", sources_used=[1, 2], created_at=now),
    )

    resp = client.get(f"/api/dossiers/{dossier_id}/thread")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["role"] == "user"
    assert body[0]["text"] == "What about the ending?"
    assert body[1]["role"] == "agent"
    assert body[1]["text"] == "Follow-up answered"
    assert body[1]["sources_used"] == [1, 2]


def test_get_thread_unknown_dossier_returns_404(client):
    resp = client.get("/api/dossiers/no-such-id/thread")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "dossier not found"
