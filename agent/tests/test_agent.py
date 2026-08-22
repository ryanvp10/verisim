"""Tests for agent.agent (Task B2): ADK agent definition + research loop.

Fully offline: the google.adk runner is always faked (FakeRunner yields
SimpleNamespace events shaped like real ADK Events). No network, no
credentials, no GEMINI_API_KEY required.
"""

import json
from types import SimpleNamespace

import pytest

from agent import (
    SYSTEM,
    build_agent,
    parse_dossier,
    run_research,
    strip_fences,
)
from tools import ToolError, parallel_extract, parallel_search


# ---------------------------------------------------------------------------
# Fake runner shaped like google.adk.runners.InMemoryRunner
# ---------------------------------------------------------------------------

def make_fake_event(payload: str) -> SimpleNamespace:
    """A fake final ADK Event: is_final_response() -> True, .content.parts[0].text."""
    return SimpleNamespace(
        is_final_response=lambda: True,
        content=SimpleNamespace(parts=[SimpleNamespace(text=payload)]),
    )


class FakeRunner:
    """Stub InMemoryRunner: records every incoming message, then yields one
    fake final Event per run() call carrying the next payload in `payloads`.
    """

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.messages = []          # texts of new_message from each run() call
        self.user_ids = []
        self.session_ids = []

    def run(self, user_id=None, session_id=None, new_message=None):
        self.user_ids.append(user_id)
        self.session_ids.append(session_id)
        self.messages.append(new_message.parts[0].text)
        idx = min(len(self.messages) - 1, len(self.payloads) - 1)
        yield make_fake_event(self.payloads[idx])


def fenced(payload: dict) -> str:
    return "```json\n" + json.dumps(payload) + "\n```"


GOOD_DOSSIER = {
    "answer": "Gatsby is set in 1922 [1].",
    "findings": ["West Egg symbolizes new money."],
    "notes": ["Two sources agreed on the setting year."],
    "sources": [
        {
            "n": 1,
            "title": "SparkNotes",
            "url": "https://example.com/gatsby",
            "excerpt": "The novel is set in the summer of 1922.",
        }
    ],
}


# ---------------------------------------------------------------------------
# strip_fences
# ---------------------------------------------------------------------------

def test_strip_fences_removes_surrounding_json_fences_and_whitespace():
    text = '   \n```json\n{"answer": "x"}\n```\n  '
    assert strip_fences(text) == '{"answer": "x"}'


# ---------------------------------------------------------------------------
# parse_dossier
# ---------------------------------------------------------------------------

def test_parse_dossier_parses_valid_json_object():
    raw = '{"answer": "a", "findings": [], "notes": [], "sources": []}'
    result = parse_dossier(raw)
    assert result == {"answer": "a", "findings": [], "notes": [], "sources": []}


def test_parse_dossier_raises_valueerror_on_garbage():
    with pytest.raises(ValueError):
        parse_dossier("this is definitely not JSON at all")


# ---------------------------------------------------------------------------
# run_research (with FakeRunner — fully offline)
# ---------------------------------------------------------------------------

def test_run_research_happy_path_returns_parsed_dict_with_one_message():
    runner = FakeRunner([fenced(GOOD_DOSSIER)])

    result = run_research("What year is The Great Gatsby set in?", runner=runner)

    for key in ("answer", "findings", "notes", "sources"):
        assert key in result
    assert result["answer"] == GOOD_DOSSIER["answer"]
    assert len(runner.messages) == 1
    assert runner.messages[0] == "What year is The Great Gatsby set in?"


def test_run_research_retry_path_sends_followup_and_returns_parsed_dict():
    good = json.dumps(GOOD_DOSSIER)
    runner = FakeRunner(["utter garbage, not json", good])

    result = run_research("q?", runner=runner)

    assert result["answer"] == GOOD_DOSSIER["answer"]
    assert len(runner.messages) == 2
    assert "ONLY valid JSON" in runner.messages[1]


def test_run_research_raises_tool_error_when_both_payloads_are_garbage():
    runner = FakeRunner(["garbage one", "still garbage two"])

    with pytest.raises(ToolError):
        run_research("q?", runner=runner)


# ---------------------------------------------------------------------------
# build_agent
# ---------------------------------------------------------------------------

def test_build_agent_uses_gemini_model_env_override(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-fake")
    agent = build_agent()
    assert agent.model == "gemini-2.0-fake"


def test_build_agent_defaults_to_flash_when_env_unset(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    agent = build_agent()
    assert agent.model == "gemini-2.5-flash"


def test_build_agent_wires_both_parallel_tools():
    agent = build_agent()
    assert parallel_search in agent.tools
    assert parallel_extract in agent.tools


def test_build_agent_sets_name_verisim_and_system_instruction():
    monkeypatch_free = build_agent()
    assert monkeypatch_free.name == "verisim"
    assert monkeypatch_free.instruction == SYSTEM
