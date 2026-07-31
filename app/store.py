from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import PATHS


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    def __init__(self, database: Path = PATHS.database) -> None:
        self.database = database
        self._schema_lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _ensure_schema(self) -> None:
        with self._schema_lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    engine TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    options_json TEXT NOT NULL DEFAULT '{}',
                    summary_json TEXT NOT NULL DEFAULT '{}',
                    artifacts_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "options_json" not in columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN options_json "
                    "TEXT NOT NULL DEFAULT '{}'"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS jobs_created ON jobs(created_at DESC)"
            )

    def create(
        self,
        job_id: str,
        engine: str,
        input_name: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, engine, status, input_name, created_at, updated_at, message,
                    options_json
                ) VALUES (
                    ?, ?, 'uploading', ?, ?, ?, 'Receiving private working copy', ?
                )
                """,
                (
                    job_id,
                    engine,
                    input_name,
                    now,
                    now,
                    json.dumps(options, ensure_ascii=False),
                ),
            )
        job = self.get(job_id)
        if job is None:
            raise RuntimeError("could not create job")
        return job

    def mark_queued(self, job_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'queued', updated_at = ?, message = 'Queued'
                WHERE id = ? AND status = 'uploading'
                """,
                (utc_now(), job_id),
            )
        if cursor.rowcount != 1:
            raise RuntimeError("job could not be queued")
        job = self.get(job_id)
        if job is None:
            raise RuntimeError("queued job disappeared")
        return job

    def update(
        self,
        job_id: str,
        *,
        status: str,
        message: str,
        error: str = "",
        summary: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
    ) -> None:
        summary_json = json.dumps(summary or {}, ensure_ascii=False)
        artifacts_json = json.dumps(artifacts or [], ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, message = ?, error = ?,
                    summary_json = ?, artifacts_json = ?
                WHERE id = ?
                """,
                (
                    status,
                    utc_now(),
                    message,
                    error,
                    summary_json,
                    artifacts_json,
                    job_id,
                ),
            )

    def interrupt_incomplete(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM jobs WHERE status IN ('uploading', 'running')"
            ).fetchall()
            connection.execute(
                """
                UPDATE jobs
                SET status = 'failed', updated_at = ?,
                    message = 'Interrupted before completion',
                    error = 'The previous local process stopped unexpectedly.'
                WHERE status IN ('uploading', 'running')
                """,
                (utc_now(),),
            )
        return [str(row["id"]) for row in rows]

    def pending_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at"
            ).fetchall()
        return [str(row["id"]) for row in rows]

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        return self._decode(row) if row else None

    def list(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        with self._connect() as connection:
            if status:
                rows = connection.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (status, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (safe_limit,),
                ).fetchall()
        return [self._decode(row) for row in rows]

    def delete(self, job_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM jobs WHERE id = ?",
                (job_id,),
            )
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM jobs")
            return cursor.rowcount

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        job = dict(row)
        try:
            job["summary"] = json.loads(job.pop("summary_json"))
        except (TypeError, ValueError):
            job["summary"] = {}
        try:
            job["options"] = json.loads(job.pop("options_json"))
        except (TypeError, ValueError):
            job["options"] = {}
        try:
            job["artifacts"] = json.loads(job.pop("artifacts_json"))
        except (TypeError, ValueError):
            job["artifacts"] = []
        return job


STORE = JobStore()
