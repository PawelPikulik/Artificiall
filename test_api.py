#!/usr/bin/env python3
"""Test suite for the Task API. Run this while the server is running on localhost:8000."""

import sys
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8000"


def _request(method, path, data=None, headers=None):
    url = f"{BASE}{path}"
    req_headers = headers or {}
    if data is not None and isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    else:
        body = data
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def test(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
        return True
    else:
        print(f"  FAIL  {name} {detail}")
        return False


def run_tests():
    passed = 0
    failed = 0

    # 1. GET /health
    print("\n[GET /health]")
    status, body = _request("GET", "/health")
    if test("returns 200", status == 200):
        passed += 1
    else:
        failed += 1
    data = json.loads(body) if body else {}
    if test("status is ok", data.get("status") == "ok", data):
        passed += 1
    else:
        failed += 1

    # 2. GET /tasks (initial seed)
    print("\n[GET /tasks - initial seed]")
    status, body = _request("GET", "/tasks")
    if test("returns 200", status == 200):
        passed += 1
    else:
        failed += 1
    tasks = json.loads(body) if body else []
    if test("has 3 seeded tasks", len(tasks) == 3, f"got {len(tasks)}"):
        passed += 1
    else:
        failed += 1
    titles = {t["title"] for t in tasks}
    expected = {"Buy groceries", "Walk the dog", "Read a book"}
    if test("seed titles match", titles == expected, titles):
        passed += 1
    else:
        failed += 1

    # 3. GET /tasks/{id}
    print("\n[GET /tasks/{id}]")
    status, body = _request("GET", "/tasks/1")
    if test("returns 200 for id=1", status == 200):
        passed += 1
    else:
        failed += 1
    task = json.loads(body) if body else {}
    if test("title is Buy groceries", task.get("title") == "Buy groceries"):
        passed += 1
    else:
        failed += 1

    status, body = _request("GET", "/tasks/99")
    if test("returns 404 for unknown id", status == 404, f"got {status}"):
        passed += 1
    else:
        failed += 1

    # 4. POST /tasks
    print("\n[POST /tasks]")
    status, body = _request("POST", "/tasks", {"title": "Run tests"})
    if test("returns 201", status == 201, f"got {status}"):
        passed += 1
    else:
        failed += 1
    created = json.loads(body) if body else {}
    new_id = created.get("id")
    if test("has id", new_id is not None, created):
        passed += 1
    else:
        failed += 1
    if test("done defaults to false", created.get("done") is False):
        passed += 1
    else:
        failed += 1

    # invalid body
    status, body = _request("POST", "/tasks", {})
    if test("returns 400 for missing title", status == 400, f"got {status}"):
        passed += 1
    else:
        failed += 1

    # 5. PUT /tasks/{id}
    print("\n[PUT /tasks/{id}]")
    status, body = _request("PUT", f"/tasks/{new_id}", {"done": True})
    if test("returns 200", status == 200):
        passed += 1
    else:
        failed += 1
    updated = json.loads(body) if body else {}
    if test("done is now true", updated.get("done") is True):
        passed += 1
    else:
        failed += 1

    status, body = _request("PUT", "/tasks/99", {"done": True})
    if test("returns 404 for unknown id", status == 404, f"got {status}"):
        passed += 1
    else:
        failed += 1

    # 6. DELETE /tasks/{id}
    print("\n[DELETE /tasks/{id}]")
    status, body = _request("DELETE", f"/tasks/{new_id}")
    if test("returns 204", status == 204, f"got {status}"):
        passed += 1
    else:
        failed += 1

    status, body = _request("DELETE", "/tasks/99")
    if test("returns 404 for unknown id", status == 404, f"got {status}"):
        passed += 1
    else:
        failed += 1

    # 7. GET /stats
    print("\n[GET /stats]")
    status, body = _request("GET", "/stats")
    if test("returns 200", status == 200):
        passed += 1
    else:
        failed += 1
    stats = json.loads(body) if body else {}
    if test("total is 3 after delete", stats.get("total") == 3, stats):
        passed += 1
    else:
        failed += 1
    if test("done is 1", stats.get("done") == 1, stats):
        passed += 1
    else:
        failed += 1
    if test("open is 2", stats.get("open") == 2, stats):
        passed += 1
    else:
        failed += 1

    # 8. Filtering & search
    print("\n[Filtering & Search]")
    status, body = _request("GET", "/tasks?done=true")
    tasks = json.loads(body) if body else []
    if test("?done=true returns 1 task", len(tasks) == 1, f"got {len(tasks)}"):
        passed += 1
    else:
        failed += 1
    if test("task is Walk the dog", tasks[0]["title"] == "Walk the dog" if tasks else False):
        passed += 1
    else:
        failed += 1

    status, body = _request("GET", "/tasks?search=Buy")
    tasks = json.loads(body) if body else []
    if test("?search=Buy returns Buy groceries", len(tasks) == 1 and tasks[0]["title"] == "Buy groceries", tasks):
        passed += 1
    else:
        failed += 1

    # 9. POST /reset
    print("\n[POST /reset]")
    # Create a temp task first to prove reset clears it
    _request("POST", "/tasks", {"title": "Temp task"})
    status, body = _request("POST", "/reset")
    if test("returns 200", status == 200):
        passed += 1
    else:
        failed += 1
    tasks = json.loads(body) if body else []
    if test("returns 3 tasks", len(tasks) == 3, f"got {len(tasks)}"):
        passed += 1
    else:
        failed += 1

    # 10. Persistence check
    print("\n[Persistence check]")
    # We already created and deleted tasks above, but the seed data should remain.
    status, body = _request("GET", "/tasks")
    tasks = json.loads(body) if body else []
    if test("seed data still present after all ops", len(tasks) == 3, f"got {len(tasks)}"):
        passed += 1
    else:
        failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("TEST SUITE FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    run_tests()
