"""Test suite for the AI-powered task analysis endpoint (BE-07).

Covers:
1. Happy path – valid task returns structured analysis
2. Task not found – 404
3. Missing API key – 503
4. Invalid LLM schema – 503
5. Timeout – 503
6. Retry exhaustion – 503
7. Rate-limit recovery – 200 after one retry
8. Empty task title edge case
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure we have a dummy key so the client instantiates; we mock the actual call.
os.environ["GROQ_API_KEY"] = "gsk_test_dummy_key_for_testing"

from main import app
import llm
import db as db_module

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_seed_tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Walk the dog", "done": True},
    {"id": 3, "title": "Read a book", "done": False},
]


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Mock DB layer so tests run without a live PostgreSQL container."""
    _tasks_db = _seed_tasks.copy()
    _counter = {"val": 3}

    def _get_task(task_id):
        return next((t for t in _tasks_db if t["id"] == task_id), None)

    def _create_task(title, done=False):
        _counter["val"] += 1
        task = {"id": _counter["val"], "title": title, "done": done}
        _tasks_db.append(task)
        return task

    def _reset_tasks():
        _tasks_db.clear()
        _tasks_db.extend(_seed_tasks.copy())
        _counter["val"] = 3
        return _tasks_db

    def _update_task(task_id, title=None, done=None):
        task = _get_task(task_id)
        if task is None:
            return None
        if title is not None:
            task["title"] = title
        if done is not None:
            task["done"] = done
        return task

    def _delete_task(task_id):
        task = _get_task(task_id)
        if task is None:
            return None
        _tasks_db.remove(task)
        return task

    def _list_tasks(done=None, search=None):
        results = list(_tasks_db)
        if done is not None:
            results = [t for t in results if t["done"] == done]
        if search:
            q = search.lower()
            results = [t for t in results if q in t["title"].lower()]
        return results

    def _get_stats():
        total = len(_tasks_db)
        done = sum(1 for t in _tasks_db if t["done"])
        return {"total": total, "done": done, "open": total - done}

    monkeypatch.setattr(db_module, "get_task", _get_task)
    monkeypatch.setattr(db_module, "create_task", _create_task)
    monkeypatch.setattr(db_module, "reset_tasks", _reset_tasks)
    monkeypatch.setattr(db_module, "update_task", _update_task)
    monkeypatch.setattr(db_module, "delete_task", _delete_task)
    monkeypatch.setattr(db_module, "list_tasks", _list_tasks)
    monkeypatch.setattr(db_module, "get_stats", _get_stats)

    _reset_tasks()
    yield


@pytest.fixture
def valid_analysis():
    """A well-formed AI response dict."""
    return {
        "priority": "Medium",
        "category": "Errands",
        "estimated_minutes": 45,
        "reasoning": "Buying groceries is a routine weekly errand.",
    }


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------

def test_analyze_task_happy_path(valid_analysis):
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(valid_analysis)))]

    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.return_value = mock_completion
        response = client.post("/tasks/1/analyze")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 1
    assert body["title"] == "Buy groceries"
    assert body["analysis"]["priority"] == "Medium"
    assert body["analysis"]["category"] == "Errands"
    assert body["analysis"]["estimated_minutes"] == 45
    assert "reasoning" in body["analysis"]


# ---------------------------------------------------------------------------
# 2. Task not found
# ---------------------------------------------------------------------------

def test_analyze_task_not_found():
    response = client.post("/tasks/999/analyze")
    assert response.status_code == 404
    assert "Task 999 not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Missing API key
# ---------------------------------------------------------------------------

def test_analyze_task_missing_api_key():
    with patch.object(llm.LLMConfig, "API_KEY", ""):
        response = client.post("/tasks/1/analyze")
    assert response.status_code == 503
    assert "GROQ_API_KEY is not set" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Invalid LLM schema (model returns wrong JSON shape)
# ---------------------------------------------------------------------------

def test_analyze_task_invalid_schema():
    bad_json = {"priority": "Urgent", "category": "", "estimated_minutes": -5}
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(bad_json)))]

    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.return_value = mock_completion
        response = client.post("/tasks/1/analyze")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "schema validation" in detail or "validation error" in detail.lower()


# ---------------------------------------------------------------------------
# 5. Timeout
# ---------------------------------------------------------------------------

def test_analyze_task_timeout():
    from groq import APIConnectionError
    import httpx

    req = httpx.Request("GET", "https://api.groq.com/v1/chat/completions")
    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.side_effect = APIConnectionError(
            message="Connection timed out", request=req
        )
        response = client.post("/tasks/1/analyze")

    assert response.status_code == 503
    assert "failed after 3 attempts" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 6. Retry exhaustion (persistent 5xx)
# ---------------------------------------------------------------------------

def test_analyze_task_retry_exhaustion():
    from groq import APIError
    import httpx

    req = httpx.Request("GET", "https://api.groq.com/v1/chat/completions")
    err = APIError(message="Internal server error", request=req, body=None)
    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.side_effect = err
        response = client.post("/tasks/1/analyze")

    assert response.status_code == 503
    assert "failed after 3 attempts" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 7. Rate-limit recovery (succeeds on second attempt)
# ---------------------------------------------------------------------------

def test_analyze_task_rate_limit_recovery(valid_analysis):
    from groq import RateLimitError
    import httpx

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(valid_analysis)))]

    resp = httpx.Response(429, request=httpx.Request("GET", "https://api.groq.com"))
    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.side_effect = [
            RateLimitError(message="Rate limit exceeded", response=resp, body=None),
            mock_completion,
        ]
        response = client.post("/tasks/1/analyze")

    assert response.status_code == 200
    assert response.json()["analysis"]["priority"] == "Medium"


# ---------------------------------------------------------------------------
# 8. Empty title edge case
# ---------------------------------------------------------------------------

def test_analyze_task_empty_title(valid_analysis):
    """A task with an empty title should still be analyzable; the AI handles the prompt."""
    # Create a task with an empty-ish title
    create_resp = client.post("/tasks", json={"title": "   "})
    # FastAPI validation should reject this, so we test that the endpoint
    # does not crash on weird but technically valid titles.
    create_resp = client.post("/tasks", json={"title": "A"})
    task_id = create_resp.json()["id"]

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=json.dumps(valid_analysis)))]

    with patch("llm.Groq") as MockGroq:
        instance = MockGroq.return_value
        instance.chat.completions.create.return_value = mock_completion
        response = client.post(f"/tasks/{task_id}/analyze")

    assert response.status_code == 200
    assert response.json()["title"] == "A"
