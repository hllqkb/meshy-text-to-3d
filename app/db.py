import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化 SQLite 数据库。"""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                preview_task_id TEXT,
                refine_task_id TEXT,
                status TEXT NOT NULL DEFAULT 'preview_pending',
                progress INTEGER DEFAULT 0,
                prompt TEXT,
                local_files TEXT,
                created_at INTEGER
            )
            """
        )
        conn.commit()


def insert_task(
    task_id: str,
    preview_task_id: str,
    status: str = "preview_pending",
    prompt: str = "",
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, preview_task_id, status, prompt, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, preview_task_id, status, prompt, int(time.time() * 1000)),
        )
        conn.commit()


def update_task(
    task_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    refine_task_id: Optional[str] = None,
    local_files: Optional[dict] = None,
    prompt: Optional[str] = None,
) -> None:
    fields = []
    values = []
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if progress is not None:
        fields.append("progress = ?")
        values.append(progress)
    if refine_task_id is not None:
        fields.append("refine_task_id = ?")
        values.append(refine_task_id)
    if local_files is not None:
        fields.append("local_files = ?")
        values.append(json.dumps(local_files))
    if prompt is not None:
        fields.append("prompt = ?")
        values.append(prompt)

    if not fields:
        return

    values.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
    with _get_conn() as conn:
        conn.execute(sql, values)
        conn.commit()


def get_task(task_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return dict(row)


def get_task_by_refine_id(refine_task_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE refine_task_id = ?", (refine_task_id,)).fetchone()
        if row is None:
            return None
        return dict(row)


def list_tasks() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_task(task_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0
