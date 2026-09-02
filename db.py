import os
import psycopg2
from psycopg2.extras import RealDictCursor

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
