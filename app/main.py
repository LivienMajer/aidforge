"""FastAPI app: serves the web UI and the generation API.

Run:  .venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8000
"""

import mimetypes
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import cad, config, gemini, pipeline
from .templates_registry import BY_ID, TEMPLATES

app = FastAPI(title=config.APP_NAME)
app.mount("/static", StaticFiles(directory=config.WEB_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=config.OUTPUT_DIR), name="outputs")

pipeline.load_saved_jobs()  # results survive restarts (demo safety net)


@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "app": config.APP_NAME,
        "openscad": bool(config.OPENSCAD),
        "gemini_key": gemini.has_key(),
        "checks": pipeline.checks_mod is not None,
        "models": {"analysis": config.ANALYSIS_MODEL, "cad": config.CAD_MODEL, "review": config.REVIEW_MODEL},
    }


@app.get("/api/templates")
def templates():
    return [
        {"id": t.id, "name": t.name, "description": t.description, "good_for": t.good_for}
        for t in TEMPLATES
    ]


def _job_or_404(job_id: str) -> pipeline.Job:
    job = pipeline.JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


def _require_key():
    if not gemini.has_key():
        raise HTTPException(400, "GEMINI_API_KEY is not set (put it into .env).")


async def _save_upload(f: UploadFile, dest: Path) -> None:
    size = 0
    with dest.open("wb") as out:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if size > config.MAX_UPLOAD_BYTES:
                raise HTTPException(413, "File too large")
            out.write(chunk)


@app.get("/api/jobs")
def list_jobs(limit: int = 30):
    jobs = sorted(pipeline.JOBS.values(), key=lambda j: j.created, reverse=True)
    return [pipeline.job_summary(j) for j in jobs if j.version > 0][:limit]


@app.post("/api/jobs")
async def create_job(
    impairment: str = Form(...),
    activity: str = Form(...),
    notes: str = Form(""),
    language: str = Form("de"),
    review: bool = Form(True),
    files: list[UploadFile] = File(default=[]),
    still: UploadFile | None = File(default=None),
):
    _require_key()
    if not config.OPENSCAD:
        raise HTTPException(500, "OpenSCAD not found. Install it or set OPENSCAD_PATH.")
    job = pipeline.Job(language=language, review=review)
    job.upload_dir.mkdir(parents=True, exist_ok=True)
    media: list[tuple[Path, str]] = []
    for i, f in enumerate(files[:6]):
        mime = f.content_type or mimetypes.guess_type(f.filename or "")[0] or ""
        if not (mime.startswith("image/") or mime.startswith("video/")):
            continue
        dest = job.upload_dir / f"input_{i}{Path(f.filename or '').suffix.lower()[:6]}"
        await _save_upload(f, dest)
        media.append((dest, mime))
        if job.visual_photo is None and mime.startswith("image/"):
            job.visual_photo = dest  # first photo is kept for the optional AI visualization
    if job.visual_photo is None and still is not None and (still.content_type or "").startswith("image/"):
        dest = job.upload_dir / "video_still.jpg"  # frame grabbed from the video in the browser
        await _save_upload(still, dest)
        job.visual_photo = dest
    threading.Thread(target=pipeline.run_generate, args=(job, media, impairment, activity, notes),
                     daemon=True).start()
    return {"job_id": job.id}


class TemplateJobIn(BaseModel):
    template_id: str
    language: str = "de"


@app.post("/api/jobs/template")
def create_template_job(body: TemplateJobIn):
    if body.template_id not in BY_ID:
        raise HTTPException(404, "Unknown template")
    job = pipeline.Job(language=body.language, review=False, steps=("compile",))
    threading.Thread(target=pipeline.run_template_only, args=(job, body.template_id), daemon=True).start()
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return _job_or_404(job_id).to_dict()


class RebuildIn(BaseModel):
    params: dict[str, float]


@app.post("/api/jobs/{job_id}/rebuild")
def rebuild(job_id: str, body: RebuildIn):
    job = _job_or_404(job_id)
    if job.status == "running" or not job.source_code:
        raise HTTPException(409, "Job is busy or has no design yet")
    if not job.lock.acquire(blocking=False):
        raise HTTPException(409, "A rebuild is already running")
    try:
        pipeline.rebuild(job, body.params)
    except cad.CadError as e:
        raise HTTPException(422, str(e))
    finally:
        job.lock.release()
    return job.to_dict()


class RefineIn(BaseModel):
    feedback: str


@app.post("/api/jobs/{job_id}/refine")
def refine(job_id: str, body: RefineIn):
    job = _job_or_404(job_id)
    if job.status == "running" or not job.source_code:
        raise HTTPException(409, "Job is busy or has no design yet")
    _require_key()
    job.status = "running"
    threading.Thread(target=pipeline.run_refine, args=(job, body.feedback), daemon=True).start()
    return {"job_id": job.id}


class VisualizeIn(BaseModel):
    with_video: bool = False


@app.post("/api/jobs/{job_id}/visualize")
def visualize(job_id: str, body: VisualizeIn):
    """On demand only: Nano Banana start/end frames, optionally an Omni transition video."""
    job = _job_or_404(job_id)
    if not job.stl:
        raise HTTPException(409, "No model yet")
    if job.visual.get("status") == "running":
        raise HTTPException(409, "Visualization already running")
    _require_key()
    job.visual = {**job.visual, "status": "running", "stage": "queued", "error": None}
    threading.Thread(target=pipeline.run_visualize, args=(job, body.with_video), daemon=True).start()
    return {"job_id": job.id}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("de")):
    _require_key()
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty recording")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Recording too long")
    try:
        text = gemini.transcribe(data, audio.content_type or "audio/webm", language)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Transcription failed: {str(e)[:200]}")
    return {"text": text}
