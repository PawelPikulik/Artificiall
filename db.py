import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://artificiall:artificiall@db:5432/artificiall")


def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def row_to_task(row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": row["done"]}


def list_tasks(done=None, search=None):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if done is not None:
        query += " AND done = %s"
        params.append(done)
    if search:
        query += " AND title ILIKE %s"
        params.append(f"%{search}%")

    query += " ORDER BY id"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


# ── Reports ─────────────────────────────────────────────────────────

def _row_to_report(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "report_type": row["report_type"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "file_path": row["file_path"],
        "error_message": row["error_message"],
        "metadata": row["metadata"],
    }


def create_report(report_type: str, user_id: str = "", metadata: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reports (report_type, user_id, status, metadata) VALUES (%s, %s, %s, %s) RETURNING *",
        (report_type, user_id, "pending", psycopg2.extras.Json(metadata or {})),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return _row_to_report(row)


def get_report(report_id: int, user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM reports WHERE id = %s AND user_id = %s", (report_id, user_id))
    else:
        cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_report(row)


def list_reports(user_id: str = None, limit: int = 50):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute(
            "SELECT * FROM reports WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (user_id, limit),
        )
    else:
        cursor.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_report(row) for row in rows]


def update_report_status(report_id: int, status: str, file_path: str = None, error_message: str = None):
    conn = get_db()
    cursor = conn.cursor()
    updates = ["status = %s"]
    params = [status]
    if status in ("completed", "failed"):
        updates.append("completed_at = NOW()")
    if file_path is not None:
        updates.append("file_path = %s")
        params.append(file_path)
    if error_message is not None:
        updates.append("error_message = %s")
        params.append(error_message)
    query = f"UPDATE reports SET {', '.join(updates)} WHERE id = %s"
    params.append(report_id)
    cursor.execute(query, params)
    conn.commit()
    cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_report(row)


def delete_report(report_id: int, user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM reports WHERE id = %s AND user_id = %s", (report_id, user_id))
    else:
        cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None
    cursor.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    conn.close()
    return _row_to_report(row)


# ── Scheduled Reports ───────────────────────────────────────────────

def _row_to_scheduled(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "report_type": row["report_type"],
        "schedule_cron": row["schedule_cron"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "active": row["active"],
        "metadata": row["metadata"],
    }


def create_scheduled_report(report_type: str, schedule_cron: str, user_id: str = "", metadata: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO scheduled_reports (report_type, user_id, schedule_cron, metadata) VALUES (%s, %s, %s, %s) RETURNING *",
        (report_type, user_id, schedule_cron, psycopg2.extras.Json(metadata or {})),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return _row_to_scheduled(row)


def list_scheduled_reports(user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM scheduled_reports WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM scheduled_reports ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_scheduled(row) for row in rows]


def get_scheduled_report(scheduled_id: int, user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM scheduled_reports WHERE id = %s AND user_id = %s", (scheduled_id, user_id))
    else:
        cursor.execute("SELECT * FROM scheduled_reports WHERE id = %s", (scheduled_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_scheduled(row)


def update_scheduled_report_active(scheduled_id: int, active: bool, user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute(
            "UPDATE scheduled_reports SET active = %s WHERE id = %s AND user_id = %s",
            (active, scheduled_id, user_id),
        )
    else:
        cursor.execute("UPDATE scheduled_reports SET active = %s WHERE id = %s", (active, scheduled_id))
    conn.commit()
    cursor.execute("SELECT * FROM scheduled_reports WHERE id = %s", (scheduled_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_scheduled(row)


def delete_scheduled_report(scheduled_id: int, user_id: str = None):
    conn = get_db()
    cursor = conn.cursor()
    if user_id is not None:
        cursor.execute("SELECT * FROM scheduled_reports WHERE id = %s AND user_id = %s", (scheduled_id, user_id))
    else:
        cursor.execute("SELECT * FROM scheduled_reports WHERE id = %s", (scheduled_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None
    cursor.execute("DELETE FROM scheduled_reports WHERE id = %s", (scheduled_id,))
    conn.commit()
    conn.close()
    return _row_to_scheduled(row)


def get_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return row_to_task(row)


def create_task(title: str, done: bool):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id",
        (title, done),
    )
    new_id = cursor.fetchone()["id"]
    conn.commit()
    conn.close()
    return {"id": new_id, "title": title, "done": done}


def update_task(task_id: int, title=None, done=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None

    updates = []
    params = []
    if title is not None:
        updates.append("title = %s")
        params.append(title)
    if done is not None:
        updates.append("done = %s")
        params.append(done)

    if updates:
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s"
        params.append(task_id)
        cursor.execute(query, params)
        conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row_to_task(row)


def delete_task(task_id: int):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return None

    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()
    return True


def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total = cursor.fetchone()["count"]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE done = TRUE")
    done_count = cursor.fetchone()["count"]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}


def reset_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks")
    cursor.execute(
        "INSERT INTO tasks (title, done) VALUES (%s, %s), (%s, %s), (%s, %s)",
        ("Buy groceries", False, "Walk the dog", True, "Read a book", False),
    )
    conn.commit()
    cursor.execute("SELECT * FROM tasks ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [row_to_task(row) for row in rows]


# ── Jobs ──────────────────────────────────────────────────────────────

def _row_to_job(row) -> dict:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "job_type": row["job_type"],
        "status": row["status"],
        "result": row["result"],
        "error_message": row["error_message"],
        "attempts": row["attempts"],
        "max_attempts": row["max_attempts"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "metadata": row["metadata"],
    }


def create_job(task_id: int, job_type: str = "task_analysis", max_attempts: int = 3, metadata: dict = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (task_id, job_type, status, max_attempts, metadata) VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (task_id, job_type, "pending", max_attempts, psycopg2.extras.Json(metadata or {})),
    )
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return _row_to_job(row)


def get_job(job_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_job(row)


def find_latest_job_for_task(task_id: int, job_type: str = "task_analysis"):
    """Find the most recent job for a given task. Used for idempotency."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM jobs WHERE task_id = %s AND job_type = %s ORDER BY created_at DESC LIMIT 1",
        (task_id, job_type),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_job(row)


def update_job_status(job_id: int, status: str, result: dict = None, error_message: str = None, attempts: int = None):
    conn = get_db()
    cursor = conn.cursor()
    updates = ["status = %s"]
    params = [status]
    if status in ("completed", "failed"):
        updates.append("completed_at = NOW()")
    if result is not None:
        updates.append("result = %s")
        params.append(psycopg2.extras.Json(result))
    if error_message is not None:
        updates.append("error_message = %s")
        params.append(error_message)
    if attempts is not None:
        updates.append("attempts = %s")
        params.append(attempts)
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = %s"
    params.append(job_id)
    cursor.execute(query, params)
    conn.commit()
    cursor.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_job(row)


def list_jobs(limit: int = 50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_job(row) for row in rows]
