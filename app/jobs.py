from __future__ import annotations

import logging
import queue
import threading
import uuid
from typing import Any

from .config import PATHS
from .engines import ENGINES
from .store import STORE
from .utils import remove_work_tree

LOGGER = logging.getLogger(__name__)


class JobRunner:
    def __init__(self) -> None:
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        for interrupted_id in STORE.interrupt_incomplete():
            remove_work_tree(PATHS.work / interrupted_id)
        self._thread = threading.Thread(
            target=self._run,
            name="local-ai-job-runner",
            daemon=True,
        )
        self._thread.start()
        for job_id in STORE.pending_ids():
            self._queue.put(job_id)

    def stop(self) -> None:
        if not self._thread:
            return
        self._queue.put(None)
        self._thread.join(timeout=10)
        self._thread = None

    def submit(
        self,
        engine: str,
        input_name: str,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        if engine not in ENGINES:
            raise KeyError(engine)
        job_id = uuid.uuid4().hex
        job = STORE.create(job_id, engine, input_name, options)
        return job

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def _run(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                if job_id is None:
                    return
                self._process(job_id)
            finally:
                self._queue.task_done()

    def _process(self, job_id: str) -> None:
        job = STORE.get(job_id)
        if not job:
            return
        work_dir = PATHS.work / job_id
        source = work_dir / str(job["input_name"])
        output_dir = PATHS.outputs / job_id
        engine = ENGINES.get(str(job["engine"]))
        if engine is None:
            STORE.update(
                job_id,
                status="failed",
                message="Unknown engine",
                error="The requested engine is no longer registered.",
            )
            remove_work_tree(work_dir)
            return

        STORE.update(job_id, status="running", message="Processing locally")
        try:
            if not source.is_file():
                raise FileNotFoundError("private working copy is missing")
            result = engine.process(source, output_dir, dict(job["options"]))
            root = output_dir.resolve()
            artifact_names: list[str] = []
            for artifact in result.artifacts:
                resolved = artifact.resolve()
                if root not in resolved.parents or not resolved.is_file():
                    raise RuntimeError("engine returned an artifact outside its output")
                artifact_names.append(resolved.relative_to(root).as_posix())
            STORE.update(
                job_id,
                status="completed",
                message="Completed",
                summary=result.summary,
                artifacts=artifact_names,
            )
        except Exception as exc:
            LOGGER.warning(
                "Local job %s failed with %s",
                job_id,
                type(exc).__name__,
            )
            error = f"{type(exc).__name__}: local processing failed"
            STORE.update(
                job_id,
                status="failed",
                message="Processing failed",
                error=error,
            )
        finally:
            remove_work_tree(work_dir)


RUNNER = JobRunner()
