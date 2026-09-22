#!/usr/bin/env python3
"""Test suite for BE-08 PDF Report Generator.

Run this while the server is running on localhost:8000 with a valid .env.
The test suite signs up a test user, logs in, generates reports, polls
for completion, downloads the PDF, and cleans up.

Usage:
    python test_reports.py
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
TEST_EMAIL = "test-reports@example.com"
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
    # Sign up (ignore 400 if already exists)
    status, _ = _request("POST", "/auth/signup", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
    # Log in
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
    report_ids = []

    # 1. Create a task_summary report
    print("\n[POST /reports - task_summary]")
    status, body = _request(
        "POST", "/reports",
        {"report_type": "task_summary"},
        _auth_headers(),
    )
    if test("returns 202", status == 202, body):
        passed += 1
    else:
        failed += 1
    data = json.loads(body) if body else {}
    task_report_id = data.get("id")
    report_ids.append(task_report_id)
    if test("has id", task_report_id is not None, data):
        passed += 1
    else:
        failed += 1
    if test("status is pending", data.get("status") == "pending", data):
        passed += 1
    else:
        failed += 1
    if test("has download_url", "/download" in data.get("download_url", ""), data):
        passed += 1
    else:
        failed += 1

    # 2. Create a book_catalog report
    print("\n[POST /reports - book_catalog]")
    status, body = _request(
        "POST", "/reports",
        {"report_type": "book_catalog"},
        _auth_headers(),
    )
    if test("returns 202", status == 202, body):
        passed += 1
    else:
        failed += 1
    data = json.loads(body) if body else {}
    book_report_id = data.get("id")
    report_ids.append(book_report_id)
    if test("has id", book_report_id is not None, data):
        passed += 1
    else:
        failed += 1

    # 3. Poll until reports complete (or fail after timeout)
    print("\n[Polling /reports/{id} for completion]")
    max_wait = 30  # seconds
    start = time.time()
    completed = {}
    while time.time() - start < max_wait:
        for rid in report_ids:
            if rid in completed:
                continue
            status, body = _request("GET", f"/reports/{rid}", headers=_auth_headers())
            if status == 200:
                data = json.loads(body)
                if data.get("status") in ("completed", "failed"):
                    completed[rid] = data["status"]
        if len(completed) == len(report_ids):
            break
        time.sleep(1)

    for rid, st in completed.items():
        if test(f"report {rid} completed", st == "completed", st):
            passed += 1
        else:
            failed += 1

    # 4. List reports
    print("\n[GET /reports]")
    status, body = _request("GET", "/reports", headers=_auth_headers())
    if test("returns 200", status == 200, body):
        passed += 1
    else:
        failed += 1
    data = json.loads(body) if body else []
    if test("returns list", isinstance(data, list)):
        passed += 1
    else:
        failed += 1

    # 5. Download a report
    print("\n[GET /reports/{id}/download]")
    if task_report_id in completed and completed[task_report_id] == "completed":
        status, body = _request("GET", f"/reports/{task_report_id}/download", headers=_auth_headers())
        if test("returns PDF", status == 200 and body.startswith("%PDF"), f"status={status}"):
            passed += 1
        else:
            failed += 1
    else:
        print(f"  SKIP  download (report not completed)")

    # 6. Delete reports
    print("\n[DELETE /reports/{id}]")
    for rid in report_ids:
        status, _ = _request("DELETE", f"/reports/{rid}", headers=_auth_headers())
        if test(f"delete {rid} returns 204", status == 204, f"status={status}"):
            passed += 1
        else:
            failed += 1

    # 7. Invalid report type
    print("\n[POST /reports - invalid type]")
    status, body = _request(
        "POST", "/reports",
        {"report_type": "invalid"},
        _auth_headers(),
    )
    if test("returns 422", status == 422, body):
        passed += 1
    else:
        failed += 1

    # 8. Unauthenticated request
    print("\n[POST /reports - no auth]")
    status, body = _request("POST", "/reports", {"report_type": "task_summary"})
    if test("returns 401/403", status in (401, 403), body):
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
