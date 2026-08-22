"""Tests for agent.tools (Task B1): Parallel search/extract wrapper.

The Parallel SDK client is always faked (MagicMock injected through
tools._get_client, SimpleNamespace objects shaped like the parallel-web 1.3.0
SDK results). These tests never touch the network.
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import tools
from tools import ToolError, parallel_extract, parallel_search


# ---------------------------------------------------------------------------
# Fake builders shaped like the real parallel-web SDK objects
# ---------------------------------------------------------------------------

def make_search_result(*hits):
    """Fake SearchResult: .results is a list of WebSearchResult."""
    return SimpleNamespace(results=list(hits))


def make_hit(url="https://example.com/a", title="Example", excerpts=("alpha",)):
    """Fake WebSearchResult: .url str, .title Optional[str], .excerpts list."""
    return SimpleNamespace(url=url, title=title, excerpts=list(excerpts))


def make_extract_result(*items):
    """Fake ExtractResponse: .results is a list of ExtractResult."""
    return SimpleNamespace(results=list(items))


def make_extract_item(url="https://example.com/a", title="Example",
                      full_content=None, excerpts=("excerpt",)):
    """Fake ExtractResult: .url, .title Optional[str], .full_content, .excerpts."""
    return SimpleNamespace(url=url, title=title,
                           full_content=full_content, excerpts=list(excerpts))


def install_fake_client(monkeypatch, search_result=None, extract_result=None):
    """Replace tools._get_client with one returning a MagicMock client."""
    client = MagicMock()
    client.search.return_value = search_result
    client.extract.return_value = extract_result
    monkeypatch.setattr(tools, "_get_client", lambda: client)
    return client


# ---------------------------------------------------------------------------
# parallel_search
# ---------------------------------------------------------------------------

def test_search_numbers_results_starting_at_one_and_incrementing(monkeypatch):
    install_fake_client(
        monkeypatch,
        search_result=make_search_result(
            make_hit(url="https://a.example.com"),
            make_hit(url="https://b.example.com"),
            make_hit(url="https://c.example.com"),
        ),
    )

    rows = parallel_search("who directed the matrix")

    assert [row["n"] for row in rows] == [1, 2, 3]


def test_search_passes_single_query_objective_and_fast_mode(monkeypatch):
    client = install_fake_client(monkeypatch, search_result=make_search_result())

    parallel_search("verisim research question")

    client.search.assert_called_once_with(
        search_queries=["verisim research question"],
        objective="verisim research question",
        mode="fast",
    )


def test_search_caps_returned_rows_at_max_results(monkeypatch):
    install_fake_client(
        monkeypatch,
        search_result=make_search_result(
            *[make_hit(url=f"https://{i}.example.com") for i in range(15)]
        ),
    )

    rows = parallel_search("q", max_results=5)

    assert len(rows) == 5
    assert rows[-1]["n"] == 5


def test_search_title_none_becomes_empty_string(monkeypatch):
    install_fake_client(
        monkeypatch,
        search_result=make_search_result(make_hit(title=None)),
    )

    rows = parallel_search("q")

    assert rows[0]["title"] == ""


def test_search_excerpt_joined_with_spaces_capped_at_exactly_500_chars(monkeypatch):
    long_a, long_b = "a" * 300, "b" * 300
    install_fake_client(
        monkeypatch,
        search_result=make_search_result(make_hit(excerpts=(long_a, long_b))),
    )

    rows = parallel_search("q")

    expected = (long_a + " " + long_b)[:500]
    assert len(rows[0]["excerpt"]) == 500
    assert rows[0]["excerpt"] == expected


def test_missing_api_key_raises_tool_error_without_building_a_client(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.setattr(tools, "_client", None)  # reset cached client first
    ctor_spy = MagicMock(name="Parallel")
    monkeypatch.setattr(tools, "Parallel", ctor_spy)

    with pytest.raises(ToolError) as excinfo:
        parallel_search("q")

    assert "PARALLEL_API_KEY" in str(excinfo.value)
    ctor_spy.assert_not_called()


def test_empty_api_key_raises_tool_error_for_extract(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "")
    monkeypatch.setattr(tools, "_client", None)  # reset cached client first

    with pytest.raises(ToolError):
        parallel_extract("https://example.com/page")


def test_get_client_builds_once_and_reuses_cached_instance(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "test-key")
    monkeypatch.setattr(tools, "_client", None)
    built = []

    def fake_ctor(api_key=None):
        obj = SimpleNamespace(api_key=api_key)
        built.append(obj)
        return obj

    monkeypatch.setattr(tools, "Parallel", fake_ctor)

    first = tools._get_client()
    second = tools._get_client()

    assert first is second
    assert len(built) == 1


def test_search_wraps_sdk_exception_into_tool_error(monkeypatch):
    client = install_fake_client(monkeypatch)
    client.search.side_effect = RuntimeError("boom: upstream 500")

    with pytest.raises(ToolError) as excinfo:
        parallel_search("q")

    assert "boom: upstream 500" in str(excinfo.value)


# ---------------------------------------------------------------------------
# parallel_extract
# ---------------------------------------------------------------------------

def test_extract_prefers_full_content_over_excerpts(monkeypatch):
    install_fake_client(
        monkeypatch,
        extract_result=make_extract_result(
            make_extract_item(full_content="FULL PAGE TEXT",
                              excerpts=("excerpt one", "excerpt two"))
        ),
    )

    assert parallel_extract("https://example.com/page") == "FULL PAGE TEXT"


def test_extract_falls_back_to_joined_excerpts_when_no_full_content(monkeypatch):
    install_fake_client(
        monkeypatch,
        extract_result=make_extract_result(
            make_extract_item(excerpts=("excerpt one", "excerpt two"))
        ),
    )

    assert parallel_extract("https://example.com/page") == "excerpt one excerpt two"


def test_extract_returns_empty_string_when_no_results(monkeypatch):
    install_fake_client(monkeypatch, extract_result=make_extract_result())

    assert parallel_extract("https://example.com/nothing") == ""


def test_extract_wraps_sdk_exception_into_tool_error(monkeypatch):
    client = install_fake_client(monkeypatch)
    client.extract.side_effect = RuntimeError("kaboom: timeout")

    with pytest.raises(ToolError) as excinfo:
        parallel_extract("https://example.com/x")

    assert "kaboom: timeout" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Import-time safety
# ---------------------------------------------------------------------------

def test_import_does_not_require_api_key_or_network(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)

    reloaded = importlib.reload(tools)

    assert reloaded._client is None
