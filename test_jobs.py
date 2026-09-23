#!/usr/bin/env python3
"""Test suite for BE-06: Background Job (AI Task Analysis).

Run this while the server is running on localhost:8000 with a valid .env.
The test suite signs up a test user, logs in, queues analysis jobs,
polls for completion, tests idempotency, and verifies failure handling.

Usage:
    python test_jobs.py
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
TEST_EMAIL = "test-jobs@example.com"
TEST_PASSWORD = "testpass123"
ACCESS_TOKEN = None


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


def _auth_headers():
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def test(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
        return True
    else:
        print(f"  FAIL  {name} {detail}")
        return False


def setup_auth():
    global ACCESS_TOKEN
    status, _ = _request("POST", "/auth/signup", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
    status, body = _request("POST", "/auth/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if status != 200:
        print(f"Login failed: {status} {body}")
        sys.exit(1)
    data = json.loads(body)
    ACCESS_TOKEN = data["access_token"]
    print(f"Authenticated as {data['user']['email']}")


def run_tests():
    passed = 0
    failed = 0

    # 1. Queue analysis for task 1 → 202 Accepted
    print("\n[POST /tasks/1/analyze - queue job]")
    status, body = _request("POST", "/tasks/1/analyze", None, _auth_headers())
    if test("returns 202", status == 202, body):
        passed += 1
    else:
        failed += 1
    data = json.loads(body) if body else {}
    job_id = data.get("job_id")
    if test("has job_id", job_id is not None, data):
        passed += 1
    else:
        failed += 1
    if test("has status_url", "/jobs/" in data.get("status_url", ""), data):
        passed += 1
    else:
        failed += 1

    # 2. Poll /jobs/{job_id} until terminal
    print(f"\n[Polling /jobs/{job_id} for completion]")
    max_wait = 45
    start = time.time()
    final_status = None
    while time.time() - start < max_wait:
        status, body = _request("GET", f"/jobs/{job_id}", None, _auth_headers())
        if status == 200:
            data = json.loads(body)
            final_status = data.get("status")
            if final_status in ("completed", "failed"):
                break
        time.sleep(1)

    if test(f"job completed or failed ({final_status})", final_status in ("completed", "failed"), f"status={final_status}"):
        passed += 1
    else:
        failed += 1

    if final_status == "completed":
        result = data.get("result")
        if test("result has analysis", result is not None and "analysis" in result, result):
            passed += 1
        else:
            failed += 1
        if test("analysis has priority", result and "priority" in result.get("analysis", {}), result):
            passed += 1
        else:
            failed += 1

    # 3. Idempotency: queue same task again → should reuse job
    print("\n[POST /tasks/1/analyze - idempotency check]")
    status, body2 = _request("POST", "/tasks/1/analyze", None, _auth_headers())
    data2 = json.loads(body2) if body2 else {}
    job_id2 = data2.get("job_id")
    if test("returns 202", status == 202, body2):
        passed += 1
    else:
        failed += 1
    if test("same job_id reused", job_id2 == job_id, f"{job_id2} vs {job_id}"):
        passed += 1
    else:
        failed += 1

    # 4. GET /tasks/1/analysis shortcut
    print("\n[GET /tasks/1/analysis]")
    status, body = _request("GET", "/tasks/1/analysis", None, _auth_headers())
    if test("returns 200", status == 200, body):
        passed += 1
    else:
        failed += 1
    if status == 200:
        data = json.loads(body)
        if test("has analysis object", "analysis" in data, data):
            passed += 1
        else:
            failed += 1

    # 5. Queue analysis for nonexistent task → 404
    print("\n[POST /tasks/99999/analyze - invalid task]")
    status, body = _request("POST", "/tasks/99999/analyze", None, _auth_headers())
    if test("returns 404", status == 404, body):
        passed += 1
    else:
        failed += 1

    # 6. GET /jobs/{invalid_id} → 404
    print("\n[GET /jobs/99999 - invalid job]")
    status, body = _request("GET", "/jobs/99999", None, _auth_headers())
    if test("returns 404", status == 404, body):
        passed += 1
    else:
        failed += 1

    # Summary
    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    setup_auth()
    ok = run_tests()
    sys.exit(0 if ok else 1)
