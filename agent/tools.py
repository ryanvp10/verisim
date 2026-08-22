"""Task B1: Parallel web tools wrapper (search/extract) for Verisim.

Thin, synchronous wrappers around the official `parallel` SDK
(parallel-web). The SDK client is built lazily on first use, so importing
this module never requires network access or an API key. All client
construction and SDK failures are surfaced as ToolError so callers get one
predictable exception type.
"""

import os
from typing import Optional

from parallel import Parallel

EXCERPT_MAX_CHARS = 500

# Cached Parallel() instance; None until the first successful _get_client().
_client: Optional[Parallel] = None


class ToolError(Exception):
    """Raised when a tool operation fails (config, network, or SDK error)."""


def _get_client() -> Parallel:
    """Return the cached Parallel client, building it lazily on first call.

    Raises:
        ToolError: If PARALLEL_API_KEY is missing or empty.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("PARALLEL_API_KEY")
        if not api_key:
            raise ToolError(
                "PARALLEL_API_KEY is missing or empty; set it before using "
                "the parallel_search / parallel_extract tools."
            )
        # api_key=None makes the SDK auto-read PARALLEL_API_KEY from env.
        _client = Parallel(api_key=None)
    return _client


def parallel_search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web via Parallel.

    Args:
        query: Natural-language search query.
        max_results: Maximum number of rows to return (default 10).

    Returns:
        List of dicts with keys: n (1-based), title ('' when None),
        url (str), excerpt (space-joined excerpts capped at 500 chars).

    Raises:
        ToolError: On missing API key or any SDK failure.
    """
    try:
        client = _get_client()
        response = client.search(
            search_queries=[query],
            objective=query,
            mode="fast",
        )
        rows = []
        for n, item in enumerate(response.results[:max_results], start=1):
            rows.append(
                {
                    "n": n,
                    "title": item.title or "",
                    "url": str(item.url),
                    "excerpt": " ".join(item.excerpts)[:EXCERPT_MAX_CHARS],
                }
            )
        return rows
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"parallel_search failed: {exc}") from exc


def parallel_extract(url: str) -> str:
    """Extract page content for a single URL via Parallel.

    Returns the first result's full_content when present, otherwise its
    space-joined excerpts. Returns '' when there are no results at all.

    Raises:
        ToolError: On missing API key or any SDK failure.
    """
    try:
        client = _get_client()
        response = client.extract(urls=[url])
        if not response.results:
            return ""
        first = response.results[0]
        if first.full_content:
            return first.full_content
        return " ".join(first.excerpts)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"parallel_extract failed for {url}: {exc}") from exc
