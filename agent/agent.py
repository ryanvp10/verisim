"""Task B2: ADK agent definition + offline-friendly research loop for Verisim.

Defines the Verisim LlmAgent (google-adk 2.7.1), a markdown-fence stripper,
a STRICT-JSON dossier parser, and `run_research`, which drives the ADK
runner synchronously and retries once when the model's reply is not valid
JSON. Importing this module never touches the network; no credentials are
needed to run the unit tests (the runner is injected/stubbed).
"""

import json
import os
import uuid
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from tools import ToolError, parallel_extract, parallel_search

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM = (
    "You are Verisim, a research assistant for screenwriters. For every "
    "user question: run parallel_search, optionally parallel_extract on the "
    "2-3 most promising URLs, then synthesize. Output STRICT JSON with keys "
    "answer (string with bracketed numeric citations like [1]), findings "
    "(list of strings), notes (list of strings), sources (list of objects "
    "with keys n int, title str, url str, excerpt str)."
)

# Sent once, in the same session, when the first reply is not valid JSON.
RETRY_PROMPT = (
    "Your previous response was not valid JSON. Return ONLY valid JSON "
    "matching the required schema, no markdown fences."
)


def build_agent(model: Optional[str] = None) -> LlmAgent:
    """Build the Verisim research agent.

    Args:
        model: Model name override; falls back to the GEMINI_MODEL env var,
            then to DEFAULT_MODEL.

    Returns:
        An LlmAgent wired with both parallel web tools.
    """
    return LlmAgent(
        name="verisim",
        model=model or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL,
        instruction=SYSTEM,
        tools=[parallel_search, parallel_extract],
    )


def strip_fences(text: str) -> str:
    """Remove surrounding markdown code fences from a model reply.

    Strips leading whitespace, drops a first line that starts with three
    backticks (optionally followed by the word json), drops a trailing line
    that is exactly three backticks, then strips whitespace again.
    """
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1] == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def parse_dossier(text: str) -> dict:
    """Parse a model reply into a dossier dict.

    Raises:
        ValueError: If the (fence-stripped) reply is not valid JSON.
    """
    cleaned = strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Reply is not valid JSON: {exc}") from exc


def run_research(question: str, runner=None) -> dict:
    """Run one research turn end-to-end and return the parsed dossier.

    Sends `question` through the runner in a fresh session; if the final
    reply is not valid JSON, sends RETRY_PROMPT once in the SAME session
    and parses again.

    Args:
        question: The user's research question.
        runner: Runner to use; defaults to an InMemoryRunner over
            build_agent() (no credentials needed to construct it).

    Returns:
        The parsed dossier dict.

    Raises:
        ToolError: If the reply is still invalid JSON after one retry.
    """
    if runner is None:
        runner = InMemoryRunner(
            agent=build_agent(),
            app_name="verisim",
            auto_create_session=True,
        )
    session_id = f"research-{uuid.uuid4().hex}"

    def _send_and_collect(message: str) -> Optional[str]:
        """Send one message; keep the LAST final-response text."""
        final_text = None
        for event in runner.run(
            user_id="verisim",
            session_id=session_id,
            new_message=types.Content(
                role="user", parts=[types.Part(text=message)]
            ),
        ):
            if event.is_final_response():
                final_text = event.content.parts[0].text
        return final_text

    try:
        return parse_dossier(_send_and_collect(question))
    except ValueError:
        pass

    # One retry, same session.
    try:
        return parse_dossier(_send_and_collect(RETRY_PROMPT))
    except ValueError as exc:
        raise ToolError(
            "Model did not return valid JSON after one retry."
        ) from exc
