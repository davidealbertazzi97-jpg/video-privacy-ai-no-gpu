from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import MAX_UPLOAD_BYTES, PATHS
from .engines import ENGINES, VIDEO_PRIVACY_ENGINE
from .jobs import RUNNER
from .product import PRODUCT
from .security import (
    TOKEN_COOKIE,
    origin_is_allowed,
    request_is_authorized,
    request_is_loopback,
    token_matches,
)
from .store import STORE
from .utils import resolve_artifact, safe_name

STATIC = PATHS.app / "static"
CHUNK_SIZE = 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    RUNNER.start()
    try:
        yield
    finally:
        RUNNER.stop()


app = FastAPI(
    title=PRODUCT.name,
    version=PRODUCT.version,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.mount("/assets", StaticFiles(directory=STATIC), name="assets")


@app.middleware("http")
async def local_security(request: Request, call_next):
    if not request_is_loopback(request):
        return JSONResponse({"detail": "Loopback access only"}, status_code=403)
    if request.url.path.startswith("/api/"):
        if not request_is_authorized(request):
            return JSONResponse({"detail": "Unauthorized local request"}, 401)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not origin_is_allowed(
            request
        ):
            return JSONResponse({"detail": "Invalid origin"}, 403)

    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"app": PRODUCT.slug, "status": "ok", "version": PRODUCT.version}


@app.get("/")
def index(token: str | None = None):
    if token_matches(token):
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            TOKEN_COOKIE,
            token,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
        return response
    return FileResponse(STATIC / "index.html")


@app.get("/api/product")
def product() -> dict[str, str]:
    return PRODUCT.public_dict()


@app.get("/api/engines")
def engines() -> list[dict[str, Any]]:
    return [engine.public_dict() for engine in ENGINES.values()]


@app.get("/api/jobs")
def list_jobs() -> list[dict[str, Any]]:
    return STORE.list()


@app.post("/api/jobs")
async def create_job(
    file: Annotated[UploadFile, File()],
    engine: Annotated[str, Form()] = VIDEO_PRIVACY_ENGINE.engine_id,
    options: Annotated[str, Form()] = "{}",
) -> dict[str, Any]:
    if engine not in ENGINES:
        raise HTTPException(400, "Engine sconosciuto")

    try:
        parsed_options = json.loads(options)
        if not isinstance(parsed_options, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(
            400, "Le opzioni devono essere in formato JSON valido"
        ) from None

    target_engine = ENGINES[engine]
    extension = Path(file.filename or "").suffix.lower()
    if extension not in target_engine.accepted_extensions:
        raise HTTPException(400, f"Estensione non supportata: {extension}")

    temp_dir = PATHS.work / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    input_name = safe_name(file.filename or "video.mp4")
    temp_file = temp_dir / input_name

    total = 0
    try:
        with temp_file.open("wb") as handle:
            while chunk := await file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Il file supera il limite massimo")
                handle.write(chunk)

        import uuid

        job_id = uuid.uuid4().hex
        job = STORE.create(
            job_id=job_id, engine=engine, input_name=input_name, options=parsed_options
        )
        job_work_dir = PATHS.work / job["id"]
        job_work_dir.mkdir(parents=True, exist_ok=True)
        job_file = job_work_dir / input_name
        temp_file.replace(job_file)

        RUNNER.enqueue(job["id"])
        return job
    finally:
        if temp_file.is_file():
            import contextlib

            with contextlib.suppress(OSError):
                temp_file.unlink()
        await file.close()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(404, "Job non trovato")
    return job


@app.delete("/api/jobs/{job_id}")
@app.post("/api/jobs/{job_id}/delete")
def delete_job(job_id: str) -> dict[str, Any]:
    deleted = STORE.delete(job_id)
    if not deleted:
        raise HTTPException(404, "Job non trovato")
    return {"status": "deleted", "job_id": job_id}


@app.delete("/api/jobs")
@app.post("/api/jobs/clear")
def clear_all_jobs() -> dict[str, Any]:
    count = STORE.clear_all()
    return {"status": "cleared", "records_removed": count}


@app.get("/api/jobs/{job_id}/artifacts/{name}")
def get_artifact(job_id: str, name: str):
    job = STORE.get(job_id)
    if job is None:
        raise HTTPException(404, "Job non trovato")

    job_output_dir = PATHS.outputs / job_id
    try:
        artifact_path = resolve_artifact(job_output_dir, name)
    except ValueError:
        raise HTTPException(403, "Accesso negato") from None

    if not artifact_path.is_file():
        raise HTTPException(404, "Artefatto non trovato")

    return FileResponse(artifact_path)
